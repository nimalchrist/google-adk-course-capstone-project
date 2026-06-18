import base64
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_STT_MODEL = "google/gemini-2.5-flash"
_API_BASE = "https://openrouter.ai/api/v1"

_LANGUAGE_PROMPTS = {
    "en": "Transcribe the following audio accurately. Return only the transcript text, nothing else.",
    "fr": "Transcris l'audio suivant avec précision. Retourne uniquement le texte transcrit.",
    "hi": "निम्नलिखित ऑडियो को सटीक रूप से ट्रांसक्राइब करें। केवल ट्रांसक्रिप्ट टेक्स्ट लौटाएं।",
}


def transcribe(audio_bytes: bytes, language: str = "en") -> str:
    if not audio_bytes:
        return ""

    if not _API_KEY:
        log.error("OPENROUTER_API_KEY not set")
        return "[STT Error: API key not configured]"

    prompt = _LANGUAGE_PROMPTS.get(language, _LANGUAGE_PROMPTS["en"])

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "model": _STT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": "wav",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 500,
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ecombot.local",
        "X-Title": "eComBot Voice",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{_API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            log.info("STT result (%s): %s", language, text[:80])
            return text
    except httpx.HTTPStatusError as exc:
        log.error("STT HTTP error: %s %s", exc.response.status_code, exc.response.text[:200])
        return f"[STT Error: {exc.response.status_code}]"
    except Exception as exc:
        log.error("STT error: %s", exc)
        return f"[STT Error: {exc}]"
