from typing import Any
import base64
import backend.constants as constants
import requests
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

BASE_ML_URL = constants.BASE_ML_URL
FACE_EP = constants.FACE_EP  # POST, {img}


def face_detector(image_bytes: bytes, image_id: str) -> dict[str, Any]:
    image_enc = base64.b64encode(image_bytes).decode("ascii")

    logger.info(f"Sending POST req. to ML Engine for face detection.")
    resp = None
    try:
        resp = requests.post(f"{BASE_ML_URL}/{FACE_EP}/", json={
            "image_id": image_id,
            "image": image_enc
        })

    except Exception as e:
        logger.error(f"Error while POST req to {FACE_EP}: {e}")
        return {
            "image_id": image_id,
            "error": f"Error while POST req to {FACE_EP}: {e}"
        }
    res = resp.json()

    logger.info(f"Face Detector Res: {res}")
    return res
