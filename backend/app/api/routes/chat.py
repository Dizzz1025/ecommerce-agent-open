import asyncio
import base64

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.shopping_agent import ShoppingAgent
from app.core.dependencies import get_shopping_agent, get_speech_service
from app.models.events import SSEEvent
from app.models.schemas import ChatRequest
from app.services.speech_service import SpeechService
from app.utils.sse import format_sse

router = APIRouter()


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    shopping_agent: ShoppingAgent = Depends(get_shopping_agent),
) -> StreamingResponse:
    should_resume = (
        payload.resume
        or bool(payload.metadata.get("resume"))
        or bool(payload.metadata.get("resume_session_id"))
    )

    async def event_stream():
        async for event in shopping_agent.stream_chat(
            session_id=payload.session_id,
            message=payload.message,
            user_id=payload.user_id or payload.metadata.get("user_id"),
            input_type=payload.input_type,
            resume=should_resume,
            new_session=payload.new_session or bool(payload.metadata.get("new_session")),
            metadata=payload.metadata,
        ):
            yield format_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream/upload")
async def stream_chat_with_image(
    message: str = Form(default=""),
    session_id: str = Form(...),
    user_id: str | None = Form(default=None),
    input_type: str = Form(default="image_text"),
    resume: bool = Form(default=False),
    resume_session_id: str | None = Form(default=None),
    new_session: bool = Form(default=False),
    image: UploadFile | None = File(default=None),
    shopping_agent: ShoppingAgent = Depends(get_shopping_agent),
) -> StreamingResponse:
    """Multipart form-data endpoint for frontend image + text queries.

    Accepts a standard file upload alongside text fields. The image is
    base64-encoded and passed into the existing multimodal pipeline via
    metadata, so it reuses all the same VisionAnalyzer / VisualQueryBuilder
    paths that the JSON endpoint uses.

    Frontend example (JavaScript):
        const form = new FormData();
        form.append("message", "有没有类似这款但便宜点的？");
        form.append("session_id", "abc123");
        form.append("user_id", "user_001");
        form.append("image", fileInput.files[0]);  // File object

        const res = await fetch("/api/chat/stream/upload", {
            method: "POST",
            body: form,
        });
        // parse SSE stream from res.body

    curl example:
        curl -N http://127.0.0.1:8000/api/chat/stream/upload \\
          -F "message=有没有类似这款？" \\
          -F "session_id=test123" \\
          -F "user_id=user_001" \\
          -F "image=@/path/to/photo.jpg"
    """
    metadata: dict = {}
    if resume_session_id:
        metadata["resume_session_id"] = resume_session_id
    effective_message = message.strip()
    should_resume = resume or bool(resume_session_id)

    if image is not None:
        contents = await image.read()
        if not contents:
            return _error_response("图片文件为空，请重新选择图片。", "IMAGE_EMPTY")
        if len(contents) > 8 * 1024 * 1024:
            return _error_response("图片超过8MB，请压缩后再上传。", "IMAGE_TOO_LARGE")
        encoded = base64.b64encode(contents).decode("ascii")
        content_type = image.content_type or "image/jpeg"
        metadata["image_base64"] = f"data:{content_type};base64,{encoded}"
        # 纯图片模式：用户没有输入文本时，自动补一句引导提示
        if not effective_message:
            effective_message = "帮我看看这张图片里的商品"

    async def event_stream():
        async for event in shopping_agent.stream_chat(
            session_id=session_id,
            message=effective_message,
            user_id=user_id,
            input_type=input_type,
            resume=should_resume,
            new_session=new_session,
            metadata=metadata,
        ):
            yield format_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _error_response(message: str, code: str) -> StreamingResponse:
    async def stream():
        yield format_sse(SSEEvent(event="error", data={"message": message, "code": code}))
        yield format_sse(SSEEvent(event="done", data={"finish_reason": "error"}))

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/stream/voice")
async def stream_chat_with_voice(
    session_id: str = Form(...),
    user_id: str | None = Form(default=None),
    resume: bool = Form(default=False),
    resume_session_id: str | None = Form(default=None),
    new_session: bool = Form(default=False),
    language: str = Form(default="zh"),
    tts_response: bool = Form(default=False),
    audio: UploadFile = File(...),
    shopping_agent: ShoppingAgent = Depends(get_shopping_agent),
    speech_service: SpeechService = Depends(get_speech_service),
) -> StreamingResponse:
    """Voice input endpoint: ASR -> existing agent stream -> optional TTS."""

    async def event_stream():
        yield format_sse(
            SSEEvent(
                event="progress",
                data={
                    "event_type": "progress_message",
                    "中文说明": "语音输入已收到，正在先转成文字。",
                    "step": 1,
                    "stage": "speech_to_text",
                    "stage_key": "speech_to_text",
                    "text": "正在识别语音内容。",
                    "detail_text": "识别完成后会自动进入原来的导购对话流程。",
                    "display_text": "正在识别语音内容。\n识别完成后会自动进入原来的导购对话流程。",
                    "display_duration_ms": 900,
                    "display_duration_sec": 0.9,
                    "can_be_replaced": True,
                },
            )
        )
        content = await audio.read()
        result = await asyncio.to_thread(
            speech_service.transcribe_bytes,
            content=content,
            filename=audio.filename,
            content_type=audio.content_type,
            language=language,
        )
        yield format_sse(SSEEvent(event="voice_transcript", data=result.model_dump()))
        if not result.ok or not result.text.strip():
            yield format_sse(SSEEvent(event="error", data={"message": result.message, "code": "VOICE_TRANSCRIBE_FAILED"}))
            yield format_sse(SSEEvent(event="done", data={"finish_reason": "voice_error"}))
            return

        metadata = {
            "voice_input": True,
            "voice_transcript": result.text,
            "asr_backend": result.backend,
        }
        if resume_session_id:
            metadata["resume_session_id"] = resume_session_id
        captured_reply = ""
        async for event in shopping_agent.stream_chat(
            session_id=session_id,
            message=result.text,
            user_id=user_id,
            input_type="voice_text",
            resume=resume or bool(resume_session_id),
            new_session=new_session,
            metadata=metadata,
        ):
            if event.event == "turn_result":
                frontend_data = event.data.get("frontend_data") or {}
                captured_reply = ((frontend_data.get("reply_message") or {}).get("text") or "").strip()
            if event.event == "done":
                if tts_response and captured_reply:
                    yield format_sse(
                        SSEEvent(
                            event="progress",
                            data={
                                "event_type": "progress_message",
                                "中文说明": "正在把系统回复转换成语音。",
                                "step": 99,
                                "stage": "text_to_speech",
                                "stage_key": "text_to_speech",
                                "text": "正在生成语音回复。",
                                "detail_text": "语音是可选增强，文字回复已经可以直接展示。",
                                "display_text": "正在生成语音回复。\n语音是可选增强，文字回复已经可以直接展示。",
                                "display_duration_ms": 900,
                                "display_duration_sec": 0.9,
                                "can_be_replaced": True,
                            },
                        )
                    )
                    tts = await asyncio.to_thread(speech_service.synthesize_text, text=captured_reply)
                    yield format_sse(SSEEvent(event="voice_output", data=tts.model_dump()))
                yield format_sse(event)
                return
            yield format_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
