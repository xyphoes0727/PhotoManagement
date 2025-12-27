from photo_service.proc_services import captioning, face_detection, embedding
from django.http import HttpResponse
from django.views.generic import View
import backend.constants as constants
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
        body_dec = self.request.body.decode()
        body = json.loads(body_dec)

        query = body.get("query")
        query = query if query else ""
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

        query_result = json.dumps(query_result)
        return HttpResponse(
            query_result, status=200)


class ImageCaptionView(View):
    def post(self, request):
        image_id = self.request.POST.get("image_id")
        if (not image_id):
            resp = json.dumps({
                "error": "No Image ID recieved"
            })
            return HttpResponse(resp, status=400)

        image = self.request.FILES.get("image")
        if (not image):
            resp = json.dumps({
                "error": "no Image recieved"
            })
            return HttpResponse(resp, status=400)

        image_bytes = image.read()

        caption = captioning.caption_image(image_bytes, image_id)
        if ("error" in caption):
            resp = json.dumps(caption)
            return HttpResponse(resp, status=500)
        logger.debug(f"Caption: {caption}")

        caption = json.dumps(caption)

        return HttpResponse(caption, status=200)


class FaceDetectionView(View):
    def post(self, request):
        image_id = self.request.POST.get("image_id")
        if (not image_id):
            resp = json.dumps({
                "error": "No Image ID recieved"
            })
            return HttpResponse(resp, status=400)

        image = self.request.FILES.get("image")
        if (not image):
            resp = json.dumps({
                "error": "no Image recieved"
            })
            return HttpResponse(resp, status=400)

        image_bytes = image.read()

        face_res = face_detection.face_detector(image_bytes, image_id)
        if ("error" in face_res):
            resp = json.dumps(face_res)
            return HttpResponse(resp, status=500)

        face_res = json.dumps(face_res)
        return HttpResponse(face_res, status=200)


class ImageUploadView(View):
    def post(self, request):
        image_id = self.request.POST.get("image_id")
        if (not image_id):
            resp = json.dumps({
                "error": "No Image ID recieved"
            })
            return HttpResponse(resp, status=400)

        image = self.request.FILES.get("image")
        if (not image):
            resp = json.dumps({
                "error": "no Image recieved"
            })
            return HttpResponse(resp, status=400)
        logger.debug(f"Image ID: {image_id} Image: {image}")

        image_bytes = image.read()

        caption = captioning.caption_image(image_bytes, image_id)
        if ("error" in caption):
            resp = json.dumps(caption)
            return HttpResponse(resp, status=500)
        caption_text = caption.get("caption")

        embedding_res = embedding.text_embedder(caption_text)
        if ("error" in embedding_res):
            resp = json.dumps(embedding_res)
            return HttpResponse(resp, status=500)

        text_embed = embedding_res.get("embed")
        try:
            pinecone_helper._upsert_to_pinecone(
                image_index, image_id, text_embed)
        except Exception as e:
            logger.error(f"Failed to upsert image embed: {e}")

        face_res = face_detection.face_detector(image_bytes, image_id)
        if ("error" in face_res):
            resp = json.dumps(face_res)
            return HttpResponse(resp, status=500)
        face_embeds = face_res.get("face_embeds")

        has_new_face = False
        try:
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


class AlbumizationView(View):
    def post(self, request):
        image_id = self.request.POST.get("image_id")
        if (not image_id):
            resp = json.dumps({
                "error": "No Image ID recieved"
            })
            return HttpResponse(resp, status=400)

        image = self.request.FILES.get("image")
        if (not image):
            resp = json.dumps({
                "error": "no Image recieved"
            })
            return HttpResponse(resp, status=400)
        logger.debug(f"Image ID: {image_id} Image: {image}")

        image_bytes = image.read()
