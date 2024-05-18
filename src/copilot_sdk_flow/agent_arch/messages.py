from pydantic import BaseModel


class ExtensionCallMessage(BaseModel):
    name: str
    args: str


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
