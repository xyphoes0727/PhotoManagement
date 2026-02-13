from dataclasses import dataclass
from typing import Any, List, Optional, Dict
from typing import Any
from pydantic import BaseModel, ValidationError
import json


class QueryRequest(BaseModel):
    query: str

    @classmethod
    def from_django_json(cls, request) -> "QueryRequest":
        try:
            body = request.body.decode()
            data = json.loads(body) if body else {}
            return cls(**data)
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            raise ValueError(f"Failed to parse QueryRequest: {e}")


class AlbumizationRequest(BaseModel):
    image_caption: str

    @classmethod
    def from_django_json(cls, request) -> "AlbumizationRequest":
        try:
            body = request.body.decode()
            data = json.loads(body) if body else {}
            return cls(**data)
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            raise ValueError(f"Failed to parse AlbumizationRequest: {e}")


class ImageFileRequest(BaseModel):
    image_id: str
    image: bytes

    @classmethod
    def from_django(cls, request) -> "ImageFileRequest":
        try:
            image_id = request.POST.get("image_id")
            if not image_id:
                raise ValueError("No image_id in form data")
            image_file = request.FILES.get("image")
            if not image_file:
                raise ValueError("No image file in form data")
            image_bytes = image_file.read()
            return cls(image_id=image_id, image=image_bytes)
        except (ValidationError, Exception) as e:
            raise ValueError(f"Failed to parse ImageFileRequest: {e}")


class CaptionResponse(BaseModel):
    image_id: Optional[str] = None
    caption: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_proc_dict(cls, data: Dict[str, Any]) -> "CaptionResponse":
        try:
            return cls(**(data or {}))
        except ValidationError as e:
            return cls(error=f"invalid caption response: {e}")


class TextEmbeddingResponse(BaseModel):
    text: Optional[str] = None
    embed: Optional[List[float]] = None
    error: Optional[str] = None

    @classmethod
    # Returns str of type as we have to use lazy model
    def from_proc_dict(cls, data: Dict[str, Any]) -> "TextEmbeddingResponse":
        try:
            return cls(**(data or {}))
        except ValidationError as e:
            return cls(error=f"invalid embedding response: {e}")


class FaceDetectionResponse(BaseModel):
    image_id: Optional[str] = None
    face_embeds: Optional[List[List[float]]] = None
    error: Optional[str] = None

    @classmethod
    def from_proc_dict(cls, data: Dict[str, Any]) -> "FaceDetectionResponse":
        try:
            return cls(**(data or {}))
        except ValidationError as e:
            return cls(error=f"invalid face detection response: {e}")


class AlbumizationResponse(BaseModel):
    tags: Optional[List[str]] = None
    error: Optional[str] = None

    @classmethod
    def from_proc_dict(cls, data: Dict[str, Any]) -> "AlbumizationResponse":
        try:
            return cls(**data)
        except ValidationError as e:
            return cls(error=f"invalid albumization response: {e}")


@dataclass
class CreateAlbumRequest:
    name: str
    description: Optional[str] = ""

    @classmethod
    def from_django_json(cls, request):
        data = json.loads(request.body)
        return cls(
            name=data.get('name', ''),
            description=data.get('description', '')
        )


@dataclass
class AddPhotosRequest:
    photoIds: List[str]

    @classmethod
    def from_django_json(cls, request):
        data = json.loads(request.body)
        return cls(
            photoIds=data.get('photoIds', [])
        )
