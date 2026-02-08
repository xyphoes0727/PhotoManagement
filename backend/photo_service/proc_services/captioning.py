from typing import Any
import base64
import requests
import constants
import logging
from photo_service.schema import CaptionResponse

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

BASE_ML_URL = constants.BASE_ML_URL
IMAGE_EP = constants.IMAGE_EP  # POST, {img}


def caption_image(image_bytes: Any, image_id: str) -> CaptionResponse:

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
        capt_resp = CaptionResponse.from_proc_dict({
            "image_id": image_id,
            "error": f"Error while POST req to {IMAGE_EP}: {e}"
        })
        return capt_resp

    res = resp.json()
    capt_resp = CaptionResponse.from_proc_dict(res)

    return capt_resp
