from photo_service.schema import QueryRequest, ImageFileRequest, AlbumizationRequest, CreateAlbumRequest, AddPhotosRequest
from photo_service.schema import CaptionResponse, AlbumizationResponse, FaceDetectionResponse, TextEmbeddingResponse
from photo_service.object_service import s3_utils
from photo_service.proc_services import captioning, face_detection, embedding, albumization
from photo_service.models import Image, Face
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.views.generic import View
from django.utils import timezone
from django.db.models import Count
import constants
import json
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from photo_service.helpers import pinecone_helper
import tempfile
import hashlib
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent  # This is backend/
yes = load_dotenv(f"{BASE_DIR}/.env")
if (not yes):
    logger.warning(f"Failed to load .env in settings.py. BASE_DIR: {BASE_DIR}")

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "photo-management-bucket")


BASE_ML_URL = constants.BASE_ML_URL
TEXT_EP = constants.TEXT_EP  # POST, {text}
IMAGE_EP = constants.IMAGE_EP  # POST
FACE_EP = constants.FACE_EP  # POST

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "pinecone_api_key")
PINECONE_IMAGE_INDEX_HOST = os.getenv(
    "PINECONE_IMAGE_INDEX_HOST", "pinecone_image_index_host")
PINECONE_FACE_INDEX_HOST = os.getenv(
    "PINECONE_FACE_INDEX_HOST", "pinecone_face_index_host")

pc = Pinecone(api_key=PINECONE_API_KEY)
image_index = pc.Index(host=PINECONE_IMAGE_INDEX_HOST)
face_index = pc.Index(host=PINECONE_FACE_INDEX_HOST)


class QueryView(View):
    def post(self, request):
        query = ""
        try:
            query_req = QueryRequest.from_django_json(self.request)
            query = query_req.query
        except Exception as e:
            logger.error(f"Error while parsing Query Request: {e}")

        if (query == ""):
            logger.warning(f"No Query received.")
            return HttpResponse({
                "query": query,
                "error": "No Query Received"
            }, status=500)

        logger.info(f"Query recieved: {query}")

        query_result = embedding.text_embedder(query)
        if ("error" in query_result):
            resp = json.dumps(query_result)
            return HttpResponse(resp, status=500)
        query_embedding = query_result.get("embed")

        matched_ids = pinecone_helper._match_query(
            image_index, query_embedding)

        query_result = json.dumps(matched_ids)
        return HttpResponse(
            query_result, status=200)


class ImageCaptionView(View):
    def post(self, request):
        image = None
        image_id = ""
        try:
            image_req = ImageFileRequest.from_django(self.request)
            image = image_req.image
            image_id = image_req.image_id
        except Exception as e:
            logger.error(f"Error while parsing Query Request: {e}")

        caption = captioning.caption_image(image, image_id)

        if (caption.error):
            resp = json.dumps(caption)
            return HttpResponse(resp, status=500)
        logger.debug(f"Caption: {caption}")

        caption = json.dumps(caption)

        return HttpResponse(caption, status=200)


class FaceDetectionView(View):
    def post(self, request):
        image = None
        image_id = ""
        try:
            image_req = ImageFileRequest.from_django(self.request)
            image = image_req.image
            image_id = image_req.image_id
        except Exception as e:
            logger.error(f"Error while parsing Query Request: {e}")

        face_res = face_detection.face_detector(image, image_id)
        if (face_res.error):
            resp = json.dumps(face_res)
            return HttpResponse(resp, status=500)

        face_res = json.dumps(face_res)
        return HttpResponse(face_res, status=200)


class AlbumizationView(View):
    def post(self, request):
        image_caption = ""
        try:
            album_req = AlbumizationRequest.from_django_json(self.request)
            image_caption = album_req.image_caption
        except Exception as e:
            logger.error(f"Error while parsing Albumization Request: {e}")

        if (image_caption == ""):
            logger.warning(f"No Query received.")
            return HttpResponse({
                "image_caption": image_caption,
                "error": "No Caption Received"
            }, status=500)

        logger.info(f"Caption recieved: {image_caption}")

        albumization_resp = albumization.albumize_image(image_caption)
        logger.debug(f"Albumization Response: {albumization_resp}")

        albumization_json = json.dumps(albumization_resp)

        return HttpResponse(albumization_json, status=200)


class ImageUploadView(View):
    def post(self, request):
        image = None
        image_id = ''
        try:
            image_req = ImageFileRequest.from_django(self.request)
            image = image_req.image
            image_id = image_req.image_id
        except Exception as e:
            logger.error(f"Error while parsing Query Request: {e}")
            return JsonResponse({"error": f"Failed to parse request: {e}"}, status=400)

        # Upload to S3 first
        try:
            object_name = f"photos/{image_id}"
            s3_utils.upload_file_object(image, S3_BUCKET_NAME, object_name)
            logger.info(f"Uploaded image to S3: {object_name}")
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            # Continue even if S3 upload fails

        caption = captioning.caption_image(image, image_id)
        if (caption.error):
            resp = json.dumps(caption)
            return HttpResponse(resp, status=500)
        caption_text = caption.caption
        caption_text = caption_text if caption_text else ""

        embedding_res = embedding.text_embedder(caption_text)
        if ("error" in embedding_res):
            resp = json.dumps(embedding_res)
            return HttpResponse(resp, status=500)

        text_embed = embedding_res.get("embed", [])
        try:
            pinecone_helper._upsert_to_pinecone(
                image_index, image_id, text_embed)
        except Exception as e:
            logger.error(f"Failed to upsert image embed: {e}")

        face_res = face_detection.face_detector(image, image_id)
        if (face_res.error):
            resp = json.dumps(face_res)
            return HttpResponse(resp, status=500)
        face_embeds = face_res.face_embeds

        has_new_face = False
        try:
            logger.debug(f"Len of face embeds: {len(face_embeds)}")
            has_new_face = pinecone_helper._match_face_embeds(
                face_index, face_embeds)
        except Exception as e:
            logger.error(f"Error while matching face embeds: {e}")

        n_faces = len(face_embeds) if face_embeds else 0

        # S3 object name for storage
        object_name = f"photos/{image_id}"

        # Get album tags from albumization service
        album_tags = []
        album_id = 0
        try:
            albumization_resp = albumization.albumize_image(caption_text)
            if albumization_resp and 'tags' in albumization_resp:
                tags_data = albumization_resp['tags']
                # Parse tags if it's a JSON string
                if isinstance(tags_data, str):
                    try:
                        parsed = json.loads(tags_data)
                        album_tags = parsed.get('tags', []) if isinstance(
                            parsed, dict) else parsed
                    except json.JSONDecodeError:
                        album_tags = []
                elif isinstance(tags_data, list):
                    album_tags = tags_data

                # Use first tag as album name and get/create album ID
                if album_tags:
                    first_tag = album_tags[0].lower().strip()
                    # Simple hash to get consistent album ID from tag name
                    album_id = abs(hash(first_tag)) % (10 ** 9)
                logger.info(
                    f"Album tags for image: {album_tags}, album_id: {album_id}")
        except Exception as e:
            logger.error(f"Failed to get albumization: {e}")

        # Save to database
        try:
            # Generate a numeric ID from the image_id string
            image_id_hash = int(hashlib.md5(
                image_id.encode()).hexdigest()[:15], 16)

            image_obj, created = Image.objects.get_or_create(
                ImageId=image_id_hash,
                defaults={
                    'ObjectName': object_name,
                    'Caption': caption_text,
                    'FaceCount': n_faces,
                    'AlbumId': album_id,
                    'CreatedAt': timezone.now(),
                    'OnPinecone': True,
                    'IsFaceRecognised': n_faces > 0
                }
            )
            if not created:
                image_obj.ObjectName = object_name
                image_obj.Caption = caption_text
                image_obj.FaceCount = n_faces
                image_obj.AlbumId = album_id
                image_obj.OnPinecone = True
                image_obj.IsFaceRecognised = n_faces > 0
                image_obj.save()
            logger.info(f"Saved image to DB: {image_id}")
        except Exception as e:
            logger.error(f"Failed to save image to DB: {e}")

        image_resp = json.dumps({
            "caption": caption_text,
            "n_faces": n_faces,
            "has_new_face": has_new_face,
            "image_id": image_id,
            "album_tags": album_tags,
            "album_id": album_id
        })
        return HttpResponse(image_resp, status=200)


class ListPhotosView(View):
    def get(self, request):
        try:
            images = Image.objects.all().order_by('-CreatedAt')
            photos = []
            for img in images:
                caption = img.Caption or ""

                # Generate presigned URL for the image
                url = None
                if img.ObjectName:
                    url = s3_utils.create_presigned_url(
                        S3_BUCKET_NAME, img.ObjectName)

                photos.append({
                    "id": str(img.ImageId),
                    "name": img.ObjectName or f"Photo {img.ImageId}",
                    "caption": caption,
                    "faceCount": img.FaceCount or 0,
                    "uploadedAt": img.CreatedAt.isoformat() if img.CreatedAt else None,
                    "url": url,
                    "albumId": img.AlbumId
                })

            return JsonResponse({"photos": photos}, status=200)
        except Exception as e:
            logger.error(f"Error listing photos: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class PhotoDetailView(View):
    def _get_image(self, photo_id):
        try:
            return Image.objects.get(ImageId=int(photo_id))
        except (ValueError, Image.DoesNotExist):
            pass

        # Try by hashing the string image_id
        try:
            image_id_hash = int(hashlib.md5(
                photo_id.encode()).hexdigest()[:15], 16)
            return Image.objects.get(ImageId=image_id_hash)
        except Image.DoesNotExist:
            pass

        # # Try by ObjectName (which includes the path)
        # try:
        #     return Image.objects.get(ObjectName__endswith=photo_id)
        # except Image.DoesNotExist:
        #     pass

        raise Image.DoesNotExist(f"Photo {photo_id} not found")

    def get(self, request, photo_id):
        try:
            img = self._get_image(photo_id)
            caption = img.Caption or ""

            url = None
            if img.ObjectName:
                url = s3_utils.create_presigned_url(
                    S3_BUCKET_NAME, img.ObjectName)

            photo = {
                "id": str(img.ImageId),
                "name": img.ObjectName or f"Photo {img.ImageId}",
                "caption": caption,
                "faceCount": img.FaceCount or 0,
                "uploadedAt": img.CreatedAt.isoformat() if img.CreatedAt else None,
                "url": url,
                "albumId": img.AlbumId
            }
            return JsonResponse(photo, status=200)
        except Image.DoesNotExist:
            return JsonResponse({"error": "Photo not found"}, status=404)
        except Exception as e:
            logger.error(f"Error getting photo {photo_id}: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, photo_id):
        try:
            img = self._get_image(photo_id)
            object_name = img.ObjectName

            # Delete from S3
            if object_name:
                try:
                    s3_utils.delete_file(S3_BUCKET_NAME, object_name)
                    logger.info(f"Deleted photo {photo_id} from S3")
                except Exception as e:
                    logger.error(f"Failed to delete from S3: {e}")

            # Delete from database
            img.delete()
            logger.info(f"Deleted photo {photo_id} from database")

            return JsonResponse({
                "success": True,
                "message": "Photo deleted successfully"
            }, status=200)
        except Image.DoesNotExist:
            return JsonResponse({"error": "Photo not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting photo {photo_id}: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class ListAlbumsView(View):
    def get(self, request):
        try:
            # Get unique album IDs and count photos in each
            album_data = Image.objects.exclude(AlbumId=0).values('AlbumId').annotate(
                photo_count=Count('ImageId')
            ).order_by('AlbumId')

            albums = []
            for album in album_data:
                album_id = album['AlbumId']
                photos_in_album = Image.objects.filter(AlbumId=album_id)
                photo_ids = [str(p.ImageId) for p in photos_in_album]

                # Get cover photo URL (first photo in album)
                cover_url = None
                first_photo = photos_in_album.first()
                if first_photo and first_photo.ObjectName:
                    cover_url = s3_utils.create_presigned_url(
                        S3_BUCKET_NAME, first_photo.ObjectName)

                # Get album name from first photo's caption or use generic name
                album_name = f"Album {album_id}"

                albums.append({
                    "id": str(album_id),
                    "name": album_name,
                    "description": "",
                    "photoIds": photo_ids,
                    "photoCount": album['photo_count'],
                    "coverPhotoUrl": cover_url,
                    "createdAt": first_photo.CreatedAt.isoformat() if first_photo and first_photo.CreatedAt else None
                })

            return JsonResponse({"albums": albums}, status=200)
        except Exception as e:
            logger.error(f"Error listing albums: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request):
        try:
            album_req = CreateAlbumRequest.from_django_json(request)

            # Generate a new album ID
            max_album = Image.objects.aggregate(
                max_album=models.Max('AlbumId'))
            new_album_id = (max_album['max_album'] or 0) + 1

            album = {
                "id": str(new_album_id),
                "name": album_req.name,
                "description": album_req.description or "",
                "photoIds": [],
                "photoCount": 0,
                "coverPhotoUrl": None,
                "createdAt": timezone.now().isoformat()
            }

            return JsonResponse(album, status=201)
        except Exception as e:
            logger.error(f"Error creating album: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class AlbumDetailView(View):
    def get(self, request, album_id):
        try:
            album_id_int = int(album_id)
            photos_in_album = Image.objects.filter(AlbumId=album_id_int)

            if not photos_in_album.exists():
                return JsonResponse({"error": "Album not found"}, status=404)

            photo_ids = [str(p.ImageId) for p in photos_in_album]

            # Get cover photo URL
            cover_url = None
            first_photo = photos_in_album.first()
            if first_photo and first_photo.ObjectName:
                cover_url = s3_utils.create_presigned_url(
                    S3_BUCKET_NAME, first_photo.ObjectName)

            album = {
                "id": album_id,
                "name": f"Album {album_id}",
                "description": "",
                "photoIds": photo_ids,
                "photoCount": len(photo_ids),
                "coverPhotoUrl": cover_url,
                "createdAt": first_photo.CreatedAt.isoformat() if first_photo and first_photo.CreatedAt else None
            }

            return JsonResponse(album, status=200)
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, album_id):
        try:
            album_id_int = int(album_id)
            # Remove album association from photos (set to 0)
            updated = Image.objects.filter(
                AlbumId=album_id_int).update(AlbumId=0)

            if updated == 0:
                return JsonResponse({"error": "Album not found"}, status=404)

            return JsonResponse({
                "success": True,
                "message": "Album deleted successfully"
            }, status=200)
        except Exception as e:
            logger.error(f"Error deleting album {album_id}: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class AlbumPhotosView(View):
    def post(self, request, album_id):
        try:
            album_id_int = int(album_id)
            add_photos_req = AddPhotosRequest.from_django_json(request)

            # Update photos with the album ID
            photo_ids = [int(pid) for pid in add_photos_req.photoIds]
            Image.objects.filter(ImageId__in=photo_ids).update(
                AlbumId=album_id_int)

            # Get updated album info
            photos_in_album = Image.objects.filter(AlbumId=album_id_int)
            updated_photo_ids = [str(p.ImageId) for p in photos_in_album]

            # Get cover photo URL
            cover_url = None
            first_photo = photos_in_album.first()
            if first_photo and first_photo.ObjectName:
                cover_url = s3_utils.create_presigned_url(
                    S3_BUCKET_NAME, first_photo.ObjectName)

            album = {
                "id": album_id,
                "name": f"Album {album_id}",
                "description": "",
                "photoIds": updated_photo_ids,
                "photoCount": len(updated_photo_ids),
                "coverPhotoUrl": cover_url,
                "createdAt": first_photo.CreatedAt.isoformat() if first_photo and first_photo.CreatedAt else None
            }

            return JsonResponse({
                "success": True,
                "message": "Photos added successfully",
                "album": album
            }, status=200)
        except Exception as e:
            logger.error(f"Error adding photos to album {album_id}: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class StatsView(View):
    def get(self, request):
        try:
            total_photos = Image.objects.count()
            total_albums = Image.objects.exclude(
                AlbumId=0).values('AlbumId').distinct().count()
            total_faces = Image.objects.aggregate(
                total=models.Sum('FaceCount'))['total'] or 0

            # Photos uploaded this month
            now = timezone.now()
            start_of_month = now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0)
            photos_this_month = Image.objects.filter(
                CreatedAt__gte=start_of_month).count()

            stats = {
                "totalPhotos": total_photos,
                "totalAlbums": total_albums,
                "totalFaces": total_faces,
                "photosThisMonth": photos_this_month
            }

            return JsonResponse(stats, status=200)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return JsonResponse({"error": str(e)}, status=500)
