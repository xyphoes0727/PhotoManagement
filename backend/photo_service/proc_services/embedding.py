from typing import Any
import requests
import backend.constants as constants
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)
BASE_ML_URL = constants.BASE_ML_URL

TEXT_EP = constants.TEXT_EP  # POST, {text}


def text_embedder(text: str) -> dict[str, Any]:

    logger.info(f"Sending POST req. to ML Engine.")
    resp = None
    try:
        resp = requests.post(f"{BASE_ML_URL}/{TEXT_EP}/{text}")
    except Exception as e:
        logger.error(f"Error while POST req to {TEXT_EP}: {e}")
        return {
            "query": text,
            "error": f"Error while POST req to {TEXT_EP}: {e}"
        }

    res = resp.json()
    # logger.debug(f"Embedding Res: {res}")

    return res
