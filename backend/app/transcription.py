"""Local faster-whisper transcription helpers."""
import logging

from .config import WHISPER_MODEL

logger = logging.getLogger(__name__)


def transcribe_video(path: str, language: str, filename: str | None = None):
    if language not in {"auto", "en", "ja"}:
        raise ValueError("Language must be auto, en, or ja")
    from faster_whisper import WhisperModel

    logger.info("Video transcription started: requested_language=%s model=%s device=cpu compute_type=int8", language, WHISPER_MODEL)
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        path,
        beam_size=1,
        vad_filter=True,
        language=None if language == "auto" else language,
    )
    transcript = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            start, end = int(segment.start), int(segment.end)
            transcript.append({
                "text": text,
                "source_ref": f"{filename or path.rsplit('/', 1)[-1]} · {start // 60:02d}:{start % 60:02d}",
                "start_seconds": start,
                "end_seconds": end,
            })
    if not transcript:
        raise ValueError("No speech was detected in the video/audio file.")
    return transcript, info
