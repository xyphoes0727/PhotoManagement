import base64
import torch
from PIL import Image
from fastapi import FastAPI
import io
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from logging import getLogger
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from deepface import DeepFace
import constants
from dotenv import load_dotenv
from pathlib import Path

MID = constants.MID
IMAGE_TOKEN_INDEX = constants.IMAGE_TOKEN_INDEX  # what the model code looks for
APPLE_REV = constants.APPLE_REV

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent  # This is ml_engine/
yes = load_dotenv(f"{BASE_DIR}/.env")
if (not yes):
    logger.warning(f"Failed to load .env in settings.py. BASE_DIR: {BASE_DIR}")


def getTokenizer():
    tok = AutoTokenizer.from_pretrained(
        MID, trust_remote_code=True, revision=APPLE_REV)
    messages = [
        {
            "role": "user",
            "content": "<image>\nOne-sentence description of only what is visibly present at a scene level. No interpretation."

        }
    ]

    rendered = tok.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    pre, post = rendered.split("<image>", 1)

    # Tokenize the text *around* the image token (no extra specials!)
    pre_ids = tok(pre,  return_tensors="pt",
                  add_special_tokens=False).input_ids
    post_ids = tok(post, return_tensors="pt",
                   add_special_tokens=False).input_ids

    # Splice in the IMAGE token id (-200) at the placeholder position
    img_tok = torch.tensor([[IMAGE_TOKEN_INDEX]], dtype=pre_ids.dtype)

    return {
        "tok": tok,
        "pre_ids": pre_ids,
        "post_ids": post_ids,
        "img_tok": img_tok
    }


def getVLM(tok_attrs: dict):
    pre_ids = tok_attrs["pre_ids"]
    post_ids = tok_attrs["post_ids"]
    img_tok = tok_attrs["img_tok"]

    # Load
    model = AutoModelForCausalLM.from_pretrained(
        MID,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
        revision=APPLE_REV
    )

    input_ids = torch.cat([pre_ids, img_tok, post_ids], dim=1).to(model.device)
    attention_mask = torch.ones_like(input_ids, device=model.device)

    return {
        "model": model,
        "input_ids": input_ids,
        "attention_mask": attention_mask
    }


tok_attrs = {}
try:
    tok_attrs = getTokenizer()
except Exception as e:
    logger.error(f"Error while getTokenizer: {e}")

vlm_attrs = {}
try:
    vlm_attrs = getVLM(tok_attrs)
except Exception as e:
    logger.error(f"Error while getVLM: {e}")


def inferVLM(tok_attrs: dict, vlm_attrs: dict, image: Image.Image) -> str:
    tok = tok_attrs["tok"]

    model = vlm_attrs["model"]
    input_ids = vlm_attrs["input_ids"]
    attention_mask = vlm_attrs["attention_mask"]

    # Process image
    px = model.get_vision_tower().image_processor(
        images=image, return_tensors="pt")["pixel_values"]
    px = px.to(model.device, dtype=model.dtype)

    # Generate
    with torch.no_grad():
        out = model.generate(
            inputs=input_ids,
            attention_mask=attention_mask,
            images=px,
            max_new_tokens=128,
        )
    description = tok.decode(out[0], skip_special_tokens=True)
    logger.info(f"description by VLM: {description}")

    return description


NOMIC_REV = "e5cf08aadaa33385f5990def41f7a23405aec398"


def getEmbedder():
    model = SentenceTransformer(
        "nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True,
        revision=NOMIC_REV)

    return {
        "model": model
    }


embed_attrs = {}
try:
    embed_attrs = getEmbedder()
except Exception as e:
    logger.error(f"Error while getEmbedder: {e}")

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


@app.post("/ml/text-embed/{text}")
def textEmbedder(text: str):
    logger.info(f"Starting embedding for text: {text}")
    logger.debug(f"embed_attrs: {embed_attrs}")
    model: SentenceTransformer = embed_attrs["model"]

    sentences = [f'clustering: {text}']
    embeddings = model.encode(sentences)

    logger.debug(f"Shape of embeddings: {embeddings.shape}")
    text_embed = embeddings[0].tolist()

    return {
        "text": text,
        "embed": text_embed
    }


class ImageData(BaseModel):
    image_id: str
    image: str


@app.post("/ml/image-caption/")
async def imageCaptioner(image_data: ImageData):
    logger.debug(f"image_id: {image_data.image_id}")
    logger.debug(f"Type of image: {type(image_data.image)}")

    file_b64 = image_data.image
    imgBytes = base64.b64decode(s=file_b64)

    logger.debug(f"Image bytes: {imgBytes[:10]}")
    img = Image.open(io.BytesIO(imgBytes)).convert("RGB")

    caption = ""
    try:
        caption = inferVLM(tok_attrs, vlm_attrs, img)
    except Exception as e:
        logger.error(f"Failed while captioning: {e}")

    return {
        "caption": caption
    }


@app.post("/ml/face-detection/")
async def faceDetection(image_data: ImageData):
    file_b64 = image_data.image
    imgBytes = base64.b64decode(s=file_b64)

    logger.debug(f"Image bytes: {imgBytes[:10]}")
    # img = Image.open(io.BytesIO(imgBytes)).convert("RGB")

    # Embed is 512 dims
    embeds = DeepFace.represent(io.BytesIO(imgBytes), model_name="Facenet512")
    logger.debug(f"Keys of one embeds object: {embeds[0].keys()}")

    face_embeddings = []
    for emb in embeds:
        embed = emb["embedding"]  # type: ignore
        face_embeddings.append(embed)

    return {
        "face_embeds": face_embeddings
    }
