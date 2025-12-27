import random
from pinecone import Vector
from logging import getLogger
import logging
from backend import constants
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = getLogger(__name__)

FACE_SIMILARITY_THRES = constants.FACE_SIMILARITY_THRES


def _upsert_to_pinecone(index, id: str, vector: list[float]):
    vec = Vector(id=id, values=vector)
    index.upsert(vectors=[
        vec
    ])


def _match_face_embeds(face_index, face_embeds: list[list[float]]):
    has_new_face = False
    for emb in face_embeds:
        matched_id = ""

        query_resp = face_index.query(top_k=1, vector=emb)
        vecs = query_resp.matches  # type: ignore
        vec = vecs[0]

        score = vec.get("score")
        if (score >= FACE_SIMILARITY_THRES):
            logger.info(
                f"Matched ID for {matched_id} with score: {score}")
            matched_id = vec.get("id")

        if (matched_id == ""):
            has_new_face = True
            face_id = str(random.randint(1000, 100000))
            logger.info(f"Upserting new Face with ID: {face_id}")

            _upsert_to_pinecone(face_index, face_id, emb)
    return has_new_face
