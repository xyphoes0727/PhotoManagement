from typing import Any
import base64
import requests
import constants
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

BASE_ML_URL = constants.BASE_ML_URL
ALBUM_EP = constants.ALBUM_EP  # POST, {img}


# TODO: upsert album references to postgres
def albumize_image(image_caption: str):

    logger.info(f"Sending POST req. to ML Engine for albumization.")

    resp = None
    try:
        resp = requests.post(f"{BASE_ML_URL}/{ALBUM_EP}/{image_caption}")

    except Exception as e:
        logger.error(f"Error while POST req to {ALBUM_EP}: {e}")
        return {
            "image_caption": image_caption,
            "error": f"Error while POST req to {ALBUM_EP}: {e}"
        }

    res = resp.json()
    return res
