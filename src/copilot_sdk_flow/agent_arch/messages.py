from pydantic import BaseModel
from promptflow.contracts.multimedia import Image
from typing import Any


class ExtensionCallMessage(BaseModel):
    name: str
    args: Any


class ExtensionReturnMessage(BaseModel):
    name: str
    content: str


class TextResponse(BaseModel):
    role: str
    content: str


class FileResponse(BaseModel):
    name: str
    url: str


class ImageResponse(BaseModel):
    content: str

    @classmethod
    def from_bytes(cls, content: bytes):
        return ImageResponse(content=Image(content).to_base64(with_type=True))


class StepNotification(BaseModel):
    type: str
    content: str
