import torch
from PIL import Image
import io
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Union
from logging import getLogger
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from deepface import DeepFace

MID = "apple/FastVLM-0.5B"
IMAGE_TOKEN_INDEX = -200  # what the model code looks for

logger = getLogger(__name__)


def getTokenizer():
    tok = AutoTokenizer.from_pretrained(MID, trust_remote_code=True)
    messages = [
        {"role": "user", "content": "<image>\nDescribe this image in detail."}
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


def getEmbedder():
    model = SentenceTransformer(
        "nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

    return {
        "model": model
    }


embedder_attrs = getEmbedder()

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


@app.post("/ml/text-embed/{text}")
def textEmbedder(text: str):
    logger.info(f"Starting embedding for text: {text}")

    model: SentenceTransformer = embedder_attrs["model"]

    sentences = [f'clustering: {text}']
    embeddings = model.encode(sentences)

    logger.debug(f"Shape of embeddings: {embeddings.shape}")
    text_embed = embeddings[0]

    return {"text_embedding": text_embed}


@app.post("/ml/image-caption/{img}")
async def imageCaptioner(file: UploadFile):
    imgBytes = await file.read()
    img = Image.open(io.BytesIO(imgBytes)).convert("RGB")

    caption = ""
    try:
        caption = inferVLM(tok_attrs, vlm_attrs, img)
    except Exception as e:
        logger.error(f"Failed while captioning: {e}")

    return {
        "caption": caption
    }


@app.post("/ml/face-detection/{img}")
async def faceDetection(file: UploadFile):
    imgBytes = await file.read()
    img = Image.open(io.BytesIO(imgBytes)).convert("RGB")
