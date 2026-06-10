from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import subprocess
import uuid
from typing import Any


@dataclass
class SpeechResult:
    ok: bool
    text: str = ""
    file_path: str | None = None
    url: str | None = None
    backend: str | None = None
    content_type: str | None = None
    message: str = ""
    debug: dict[str, Any] | None = None

    def model_dump(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "file_path": self.file_path,
            "url": self.url,
            "backend": self.backend,
            "content_type": self.content_type,
            "message": self.message,
            "debug": self.debug or {},
        }


class SpeechService:
    """Speech-to-text and text-to-speech adapter with local fallbacks."""

    def __init__(
        self,
        *,
        enabled: bool,
        upload_dir: Path,
        tts_dir: Path,
        asr_backend: str = "auto",
        asr_model_name: str = "base",
        tts_backend: str = "auto",
        tts_voice: str = "zh-CN-XiaoxiaoNeural",
        macos_tts_voice: str = "Ting-Ting",
        max_audio_mb: int = 20,
    ) -> None:
        self.enabled = enabled
        self.upload_dir = upload_dir
        self.tts_dir = tts_dir
        self.asr_backend = asr_backend
        self.asr_model_name = asr_model_name
        self.tts_backend = tts_backend
        self.tts_voice = tts_voice
        self.macos_tts_voice = macos_tts_voice
        self.max_audio_bytes = max_audio_mb * 1024 * 1024
        self._faster_whisper_model = None
        self._whisper_model = None
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.tts_dir.mkdir(parents=True, exist_ok=True)

    def transcribe_bytes(
        self,
        *,
        content: bytes,
        filename: str | None,
        content_type: str | None = None,
        language: str = "zh",
    ) -> SpeechResult:
        if not self.enabled:
            return SpeechResult(ok=False, message="语音功能未启用。", backend="disabled")
        if not content:
            return SpeechResult(ok=False, message="音频文件为空。", backend="input_validation")
        if len(content) > self.max_audio_bytes:
            return SpeechResult(ok=False, message=f"音频超过 {self.max_audio_bytes // 1024 // 1024}MB，请压缩后再上传。", backend="input_validation")

        path = self._save_upload(content, filename)
        backends = [self.asr_backend] if self.asr_backend != "auto" else ["faster_whisper", "openai_whisper"]
        errors: list[dict[str, str]] = []
        for backend in backends:
            try:
                if backend == "faster_whisper":
                    text = self._transcribe_faster_whisper(path, language=language)
                elif backend == "openai_whisper":
                    text = self._transcribe_openai_whisper(path, language=language)
                else:
                    errors.append({"backend": backend, "error": "unsupported_asr_backend"})
                    continue
                text = text.strip()
                if text:
                    return SpeechResult(
                        ok=True,
                        text=text,
                        file_path=str(path),
                        backend=backend,
                        content_type=content_type,
                        message="语音识别成功。",
                        debug={"tried_backends": backends, "errors": errors},
                    )
                errors.append({"backend": backend, "error": "empty_transcript"})
            except Exception as exc:
                errors.append({"backend": backend, "error": f"{exc.__class__.__name__}: {exc}"})
        return SpeechResult(
            ok=False,
            file_path=str(path),
            backend="auto",
            content_type=content_type,
            message="语音识别失败：请安装 faster-whisper 或 openai-whisper，或检查音频格式。",
            debug={"tried_backends": backends, "errors": errors},
        )

    def synthesize_text(self, *, text: str, voice: str | None = None) -> SpeechResult:
        if not self.enabled:
            return SpeechResult(ok=False, message="语音功能未启用。", backend="disabled")
        text = (text or "").strip()
        if not text:
            return SpeechResult(ok=False, message="待合成文本为空。", backend="input_validation")
        text = text[:600]
        backends = [self.tts_backend] if self.tts_backend != "auto" else ["edge_tts", "macos_say"]
        errors: list[dict[str, str]] = []
        for backend in backends:
            try:
                if backend == "edge_tts":
                    path = self._synthesize_edge_tts(text=text, voice=voice or self.tts_voice)
                    return SpeechResult(
                        ok=True,
                        text=text,
                        file_path=str(path),
                        url=f"/static/tts/{path.name}",
                        backend=backend,
                        content_type="audio/mpeg",
                        message="语音合成成功。",
                        debug={"voice": voice or self.tts_voice, "tried_backends": backends},
                    )
                if backend == "macos_say":
                    path = self._synthesize_macos_say(text=text, voice=voice or self.macos_tts_voice)
                    return SpeechResult(
                        ok=True,
                        text=text,
                        file_path=str(path),
                        url=f"/static/tts/{path.name}",
                        backend=backend,
                        content_type="audio/aiff",
                        message="语音合成成功。",
                        debug={"voice": voice or self.macos_tts_voice, "tried_backends": backends},
                    )
                errors.append({"backend": backend, "error": "unsupported_tts_backend"})
            except Exception as exc:
                errors.append({"backend": backend, "error": f"{exc.__class__.__name__}: {exc}"})
        return SpeechResult(
            ok=False,
            text=text,
            backend="auto",
            message="语音合成失败：请安装 edge-tts，或确认当前 macOS 可使用 say 命令。",
            debug={"tried_backends": backends, "errors": errors},
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "asr_backend": self.asr_backend,
            "asr_model_name": self.asr_model_name,
            "tts_backend": self.tts_backend,
            "tts_voice": self.tts_voice,
            "macos_tts_voice": self.macos_tts_voice,
            "upload_dir": str(self.upload_dir),
            "tts_dir": str(self.tts_dir),
        }

    def _save_upload(self, content: bytes, filename: str | None) -> Path:
        suffix = Path(filename or "audio.wav").suffix.lower()
        if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".webm"}:
            suffix = ".wav"
        path = self.upload_dir / f"voice_{uuid.uuid4().hex}{suffix}"
        path.write_bytes(content)
        return path

    def _transcribe_faster_whisper(self, path: Path, *, language: str) -> str:
        from faster_whisper import WhisperModel

        if self._faster_whisper_model is None:
            self._faster_whisper_model = WhisperModel(self.asr_model_name, device="cpu", compute_type="int8")
        segments, _info = self._faster_whisper_model.transcribe(str(path), language=language or "zh", vad_filter=True)
        return "".join(segment.text for segment in segments)

    def _transcribe_openai_whisper(self, path: Path, *, language: str) -> str:
        import whisper

        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(self.asr_model_name, device="cpu")
        result = self._whisper_model.transcribe(str(path), language=language or "zh", fp16=False)
        return str(result.get("text") or "")

    def _synthesize_edge_tts(self, *, text: str, voice: str) -> Path:
        import edge_tts

        path = self.tts_dir / f"tts_{uuid.uuid4().hex}.mp3"

        async def run() -> None:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(str(path))

        asyncio.run(run())
        return path

    def _synthesize_macos_say(self, *, text: str, voice: str) -> Path:
        path = self.tts_dir / f"tts_{uuid.uuid4().hex}.aiff"
        subprocess.run(
            ["say", "-v", voice, "-o", str(path), text],
            check=True,
            timeout=30,
            capture_output=True,
            text=True,
        )
        return path
