from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.dependencies import get_speech_service
from app.services.speech_service import SpeechService

router = APIRouter()


@router.get("/diagnostics")
async def speech_diagnostics(speech_service: SpeechService = Depends(get_speech_service)) -> dict:
    return {
        "中文说明": "语音模块诊断信息。ASR 优先 faster-whisper/openai-whisper，TTS 优先 edge-tts，macOS 可 fallback 到 say。",
        **speech_service.diagnostics(),
    }


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str = Form(default="zh"),
    speech_service: SpeechService = Depends(get_speech_service),
) -> dict:
    content = await audio.read()
    result = await asyncio.to_thread(
        speech_service.transcribe_bytes,
        content=content,
        filename=audio.filename,
        content_type=audio.content_type,
        language=language,
    )
    return {
        "中文说明": "语音转文字结果。ok=true 时 text 可直接作为 chat message 使用。",
        **result.model_dump(),
    }


@router.post("/synthesize")
async def synthesize_voice(
    text: str = Form(...),
    voice: str | None = Form(default=None),
    speech_service: SpeechService = Depends(get_speech_service),
) -> dict:
    result = await asyncio.to_thread(speech_service.synthesize_text, text=text, voice=voice)
    return {
        "中文说明": "文字转语音结果。ok=true 时 url 可由前端播放。",
        **result.model_dump(),
    }
