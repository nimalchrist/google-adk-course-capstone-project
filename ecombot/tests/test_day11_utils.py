import sys
sys.path.insert(0, ".")
import time

from src.voice.metrics import VoiceMetrics, print_metrics_table
from src.voice.languages import get_language, LANGUAGES

# Test metrics
m = VoiceMetrics()
t = m.start_turn()
t.turn_number = 1
t.user_text = "Where is my order ORD-001?"
t.speech_end_time = time.time()
t.stt_start_time = t.speech_end_time
t.stt_end_time = t.speech_end_time + 0.4
t.agent_start_time = t.stt_end_time
t.agent_end_time = t.agent_start_time + 0.8
t.tts_start_time = t.agent_end_time
t.tts_first_audio_time = t.tts_start_time + 0.3
t.playback_start_time = t.tts_first_audio_time
t.tts_end_time = t.tts_start_time + 1.0
m.end_turn()

t2 = m.start_turn()
t2.turn_number = 2
t2.user_text = "Recommend a phone under 30k"
t2.speech_end_time = time.time()
t2.stt_start_time = t2.speech_end_time
t2.stt_end_time = t2.speech_end_time + 0.35
t2.agent_start_time = t2.stt_end_time
t2.agent_end_time = t2.agent_start_time + 1.5
t2.tts_start_time = t2.agent_end_time
t2.tts_first_audio_time = t2.tts_start_time + 0.25
t2.playback_start_time = t2.tts_first_audio_time
t2.tts_end_time = t2.tts_start_time + 0.8
m.end_turn()

print_metrics_table(m)

# Test languages
print("Languages:", list(LANGUAGES.keys()))
en = get_language("en")
print(f"EN greeting: {en.greeting[:50]}...")
fr = get_language("fr")
print(f"FR greeting: {fr.greeting[:50]}...")
print()
print("All utility tests passed!")
