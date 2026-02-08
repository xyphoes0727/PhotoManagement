from photo_service.schema import QueryRequest, ImageFileRequest, AlbumizationRequest
from photo_service.schema import CaptionResponse, AlbumizationResponse, FaceDetectionResponse, TextEmbeddingResponse
from photo_service.proc_services import captioning, face_detection, embedding, albumization
from django.http import HttpResponse
from django.views.generic import View
import constants
import json
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from photo_service.helpers import pinecone_helper

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent  # This is backend/
yes = load_dotenv(f"{BASE_DIR}/.env")
if (not yes):
    logger.warning(f"Failed to load .env in settings.py. BASE_DIR: {BASE_DIR}")


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


# TODO: ADD ALBUMIZATION HERE
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

        n_faces = len(face_embeds)
        image_resp = json.dumps({
            "caption": caption_text,
            "n_faces": n_faces,
            "has_new_face": has_new_face
        })
        return HttpResponse(image_resp, status=200)

class ListPhotos(View):
    def get(self, request):
        