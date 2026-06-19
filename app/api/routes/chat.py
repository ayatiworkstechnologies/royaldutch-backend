from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chat_service import get_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    history = [{"role": m.role, "content": m.content} for m in body.messages]
    reply = get_chat_response(history)
    return ChatResponse(reply=reply)
