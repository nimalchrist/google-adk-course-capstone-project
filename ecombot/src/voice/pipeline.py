import argparse
import asyncio
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("voice-pipeline")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.orchestrator import orchestrator_agent
from src.voice.languages import get_language, LANGUAGES
from src.voice.metrics import VoiceMetrics, print_metrics_table, TurnMetrics
from src.voice.stt_openrouter import transcribe
from src.voice.tts_openrouter import synthesize, synthesize_streaming


_VOICE_STYLE = """

VOICE OUTPUT RULES (you are speaking, not typing):
- Reply in the SAME language the user spoke.
- Use plain spoken sentences only — NO markdown, lists, emoji, tables, or code.
- Keep answers to 2–3 short sentences for simple queries.
- For complex answers, break into short spoken paragraphs.
- Confirm easily-misheard IDs before calling tools (e.g., "I heard order ID
  O-R-D-zero-zero-one. Is that correct?").
- Ask ONE short clarifying question if the request is unclear, instead of guessing.
- Numbers: say "thirty thousand" not "30,000".
- Prices: say "rupees" not "₹".
"""


class VoicePipeline:

    def __init__(
        self,
        language: str = "en",
        enable_barge_in: bool = True,
        text_mode: bool = False,
    ):
        self.lang = get_language(language)
        self.enable_barge_in = enable_barge_in
        self.text_mode = text_mode
        self.metrics = VoiceMetrics()
        self._running = False

        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=orchestrator_agent,
            app_name="ecombot_voice",
            session_service=self._session_service,
        )
        self._session = None
        self._user_id = "voice_user"

        self._audio_io = None

    async def _init_session(self):
        self._session = await self._session_service.create_session(
            app_name="ecombot_voice",
            user_id=self._user_id,
        )

    def _get_audio_io(self):
        if self._audio_io is None:
            from src.voice.audio_io import AudioIO
            self._audio_io = AudioIO(enable_barge_in=self.enable_barge_in)
        return self._audio_io

    async def _agent_turn(self, text: str) -> str:
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        )

        final_text = ""
        async for event in self._runner.run_async(
            user_id=self._session.user_id,
            session_id=self._session.id,
            new_message=user_content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    texts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                    if texts:
                        final_text = "\n".join(texts)

        return final_text

    def _needs_confirmation(self, text: str) -> tuple[bool, str]:
        match = re.search(r"(ORD-\d{3,})", text, re.IGNORECASE)
        if match:
            order_id = match.group(1).upper()
            spelled = " ".join(order_id)
            return True, f"I heard order ID {spelled}. Is that correct?"
        return False, ""

    def _is_confirmation(self, text: str) -> bool | None:
        lower = text.lower().strip()
        if any(word in lower for word in self.lang.confirm_yes):
            return True
        if any(word in lower for word in self.lang.confirm_no):
            return False
        return None

    async def run(self):
        await self._init_session()
        self._running = True

        print(f"\n{'='*60}")
        print(f"  🎙️  eComBot Voice Pipeline — {self.lang.name}")
        print(f"{'='*60}")
        print(f"  Mode: {'Text (keyboard)' if self.text_mode else 'Voice (microphone)'}")
        print(f"  Barge-in: {'enabled' if self.enable_barge_in else 'disabled'}")
        print(f"  Say 'quit' or 'exit' to stop.")
        print(f"{'='*60}\n")

        greeting = self.lang.greeting
        print(f"  🤖 {greeting}")
        if not self.text_mode:
            audio = synthesize(greeting, self.lang.voice)
            if audio:
                self._get_audio_io().speak(audio)

        pending_confirmation = None  # (original_text, confirmed_text_to_send)

        while self._running:
            try:
                turn = self.metrics.start_turn()

                if self.text_mode:
                    user_text = input("\n  🎤 You: ").strip()
                    turn.speech_end_time = time.time()
                    turn.stt_start_time = turn.speech_end_time
                    turn.stt_end_time = turn.speech_end_time
                else:
                    aio = self._get_audio_io()
                    audio_bytes = aio.listen_utterance()
                    turn.speech_end_time = time.time()

                    if not audio_bytes:
                        self.metrics._turn_counter -= 1  # Don't count empty turns
                        continue

                    turn.stt_start_time = time.time()
                    user_text = transcribe(audio_bytes, self.lang.code)
                    turn.stt_end_time = time.time()

                    if not user_text or user_text.startswith("[STT Error"):
                        print(f"  ⚠️ Could not understand. Please try again.")
                        self.metrics._turn_counter -= 1
                        continue

                    print(f"\n  🎤 You: {user_text}")

                turn.user_text = user_text

                if user_text.lower().strip() in ("quit", "exit", "q", "stop"):
                    print("\n  👋 Goodbye!")
                    self._running = False
                    break

                if pending_confirmation is not None:
                    confirmed = self._is_confirmation(user_text)
                    if confirmed is True:
                        user_text = pending_confirmation
                        pending_confirmation = None
                    elif confirmed is False:
                        pending_confirmation = None
                        reply = "No problem. Please tell me the correct order ID."
                        print(f"  🤖 {reply}")
                        if not self.text_mode:
                            audio = synthesize(reply, self.lang.voice)
                            if audio:
                                self._get_audio_io().speak(audio)
                        self.metrics.end_turn()
                        continue
                    else:
                        pending_confirmation = None

                needs_confirm, confirm_prompt = self._needs_confirmation(user_text)
                if needs_confirm and pending_confirmation is None:
                    pending_confirmation = user_text
                    print(f"  🤖 {confirm_prompt}")
                    if not self.text_mode:
                        audio = synthesize(confirm_prompt, self.lang.voice)
                        if audio:
                            self._get_audio_io().speak(audio)
                    self.metrics.end_turn()
                    continue

                turn.agent_start_time = time.time()
                reply = await self._agent_turn(user_text)
                turn.agent_end_time = time.time()

                if not reply:
                    reply = "I'm sorry, I didn't get a response. Could you try again?"

                print(f"  🤖 {reply}")

                if not self.text_mode:
                    turn.tts_start_time = time.time()
                    aio = self._get_audio_io()

                    sentences = re.split(r'(?<=[.!?])\s+', reply.strip())
                    first_audio = True

                    for sentence in sentences:
                        if not sentence.strip():
                            continue

                        audio = synthesize(sentence.strip(), self.lang.voice)
                        if first_audio and audio:
                            turn.tts_first_audio_time = time.time()
                            turn.playback_start_time = time.time()
                            first_audio = False

                        if audio:
                            aio.speak(audio)
                            if aio.was_interrupted:
                                log.info("Barge-in: remaining sentences skipped")
                                break

                    turn.tts_end_time = time.time()
                else:
                    turn.tts_start_time = time.time()
                    turn.tts_first_audio_time = time.time()
                    turn.tts_end_time = time.time()
                    turn.playback_start_time = time.time()

                completed_turn = self.metrics.end_turn()
                print(f"  ⏱️ [{completed_turn.stt_ms}ms STT + "
                      f"{completed_turn.agent_ms}ms Agent + "
                      f"{completed_turn.tts_ttfb_ms}ms TTS = "
                      f"{completed_turn.mouth_to_ear_ms}ms] "
                      f"{completed_turn.verdict}")

            except KeyboardInterrupt:
                print("\n\n  👋 Interrupted. Goodbye!")
                self._running = False
                break
            except Exception as exc:
                log.error("Pipeline error: %s", exc)
                print(f"  ❌ Error: {exc}")
                if self.metrics._current:
                    self.metrics.end_turn()

        print_metrics_table(self.metrics)


def main():
    parser = argparse.ArgumentParser(description="eComBot Voice Pipeline")
    parser.add_argument("-l", "--language", default="en", choices=list(LANGUAGES.keys()),
                        help="Language code (default: en)")
    parser.add_argument("--no-barge-in", action="store_true",
                        help="Disable barge-in (interruption) detection")
    parser.add_argument("--text", action="store_true",
                        help="Text mode: use keyboard instead of microphone")
    args = parser.parse_args()

    pipeline = VoicePipeline(
        language=args.language,
        enable_barge_in=not args.no_barge_in,
        text_mode=args.text,
    )

    asyncio.run(pipeline.run())


if __name__ == "__main__":
    main()
