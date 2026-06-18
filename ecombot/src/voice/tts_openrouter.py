import logging
import os
from typing import Generator

import httpx
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_TTS_MODEL = "openai/tts-1"
_API_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_VOICE = "nova"


def synthesize(text: str, voice: str = _DEFAULT_VOICE) -> bytes:
    if not text.strip():
        return b""

    if not _API_KEY:
        log.error("OPENROUTER_API_KEY not set")
        return b""

    payload = {
        "model": _TTS_MODEL,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": 1.0,
    }

    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ecombot.local",
        "X-Title": "eComBot Voice",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{_API_BASE}/audio/speech", json=payload, headers=headers)
            resp.raise_for_status()
            audio_data = resp.content
            log.info("TTS synthesized %d bytes for: %s", len(audio_data), text[:50])
            return audio_data
    except httpx.HTTPStatusError as exc:
        log.error("TTS HTTP error: %s %s", exc.response.status_code, exc.response.text[:200])
        return b""
    except Exception as exc:
        log.error("TTS error: %s", exc)
        return b""


def synthesize_streaming(text: str, voice: str = _DEFAULT_VOICE) -> Generator[bytes, None, None]:
    sentences = _split_sentences(text)
    for sentence in sentences:
        chunk = synthesize(sentence.strip(), voice)
        if chunk:
            yield chunk


def _split_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]
