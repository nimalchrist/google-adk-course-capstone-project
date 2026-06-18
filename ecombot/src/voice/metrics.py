import logging
import time
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

BUDGET_TOTAL_MS = 1500
WARN_TOTAL_MS = 2500
SLOW_TOTAL_MS = 4000


@dataclass
class TurnMetrics:
    turn_number: int = 0
    user_text: str = ""

    speech_end_time: float = 0.0
    stt_start_time: float = 0.0
    stt_end_time: float = 0.0
    agent_start_time: float = 0.0
    agent_end_time: float = 0.0
    tts_start_time: float = 0.0
    tts_first_audio_time: float = 0.0
    tts_end_time: float = 0.0
    playback_start_time: float = 0.0

    @property
    def stt_ms(self) -> int:
        if self.stt_end_time and self.stt_start_time:
            return round((self.stt_end_time - self.stt_start_time) * 1000)
        return 0

    @property
    def agent_ms(self) -> int:
        if self.agent_end_time and self.agent_start_time:
            return round((self.agent_end_time - self.agent_start_time) * 1000)
        return 0

    @property
    def tts_ttfb_ms(self) -> int:
        if self.tts_first_audio_time and self.tts_start_time:
            return round((self.tts_first_audio_time - self.tts_start_time) * 1000)
        return 0

    @property
    def tts_total_ms(self) -> int:
        if self.tts_end_time and self.tts_start_time:
            return round((self.tts_end_time - self.tts_start_time) * 1000)
        return 0

    @property
    def mouth_to_ear_ms(self) -> int:
        if self.playback_start_time and self.speech_end_time:
            return round((self.playback_start_time - self.speech_end_time) * 1000)
        return self.stt_ms + self.agent_ms + self.tts_ttfb_ms

    @property
    def verdict(self) -> str:
        total = self.mouth_to_ear_ms
        if total <= BUDGET_TOTAL_MS:
            return "✅ PASS"
        elif total <= WARN_TOTAL_MS:
            return "⚠️ WARN"
        else:
            return "🐌 SLOW"


class VoiceMetrics:

    def __init__(self):
        self.turns: list[TurnMetrics] = []
        self._current: Optional[TurnMetrics] = None
        self._turn_counter = 0

    def start_turn(self) -> TurnMetrics:
        self._turn_counter += 1
        self._current = TurnMetrics(turn_number=self._turn_counter)
        return self._current

    def end_turn(self) -> TurnMetrics:
        if self._current:
            self.turns.append(self._current)
            turn = self._current
            self._current = None
            return turn
        return TurnMetrics()

    @property
    def current(self) -> Optional[TurnMetrics]:
        return self._current

    def summary(self) -> dict:
        if not self.turns:
            return {"turns": 0}

        totals = [t.mouth_to_ear_ms for t in self.turns]
        return {
            "turns": len(self.turns),
            "avg_total_ms": round(sum(totals) / len(totals)),
            "min_total_ms": min(totals),
            "max_total_ms": max(totals),
            "passes": sum(1 for t in self.turns if "PASS" in t.verdict),
            "warns": sum(1 for t in self.turns if "WARN" in t.verdict),
            "slows": sum(1 for t in self.turns if "SLOW" in t.verdict),
        }


def print_metrics_table(metrics: VoiceMetrics) -> None:
    if not metrics.turns:
        print("  No turns recorded.")
        return

    header = f"{'#':>3} {'STT':>6} {'Agent':>7} {'TTS↓':>6} {'Total':>7} {'Verdict':>10}  {'Transcript'}"
    sep = "─" * 75
    print(f"\n  {sep}")
    print(f"  📊 Voice Pipeline Latency Report")
    print(f"  {sep}")
    print(f"  {header}")
    print(f"  {'─'*3} {'─'*6} {'─'*7} {'─'*6} {'─'*7} {'─'*10}  {'─'*20}")

    for t in metrics.turns:
        transcript = t.user_text[:25] + "..." if len(t.user_text) > 25 else t.user_text
        print(
            f"  {t.turn_number:>3} "
            f"{t.stt_ms:>5}ms "
            f"{t.agent_ms:>6}ms "
            f"{t.tts_ttfb_ms:>5}ms "
            f"{t.mouth_to_ear_ms:>6}ms "
            f"{t.verdict:>10}  "
            f"{transcript}"
        )

    print(f"  {sep}")

    s = metrics.summary()
    print(f"  Avg: {s['avg_total_ms']}ms | "
          f"Min: {s['min_total_ms']}ms | "
          f"Max: {s['max_total_ms']}ms | "
          f"Pass: {s['passes']}/{s['turns']}")
    print(f"  Budget: {BUDGET_TOTAL_MS}ms | Warn: {WARN_TOTAL_MS}ms | Slow: {SLOW_TOTAL_MS}ms")
    print()
