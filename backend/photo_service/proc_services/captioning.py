from typing import Any
import base64
import requests
import backend.constants as constants
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

BASE_ML_URL = constants.BASE_ML_URL
IMAGE_EP = constants.IMAGE_EP  # POST, {img}


def caption_image(image_bytes: Any, image_id: str) -> dict[str, str]:

    image_enc = base64.b64encode(image_bytes).decode("ascii")

    logger.info(f"Sending POST req. to ML Engine for image captioning.")
    resp = None
    try:
        resp = requests.post(f"{BASE_ML_URL}/{IMAGE_EP}/", json={
            "image_id": image_id,
            "image": image_enc
        })

    except Exception as e:
        logger.error(f"Error while POST req to {IMAGE_EP}: {e}")
        return {
            "image_id": image_id,
            "error": f"Error while POST req to {IMAGE_EP}: {e}"
        }

    res = resp.json()

    return res
