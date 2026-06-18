import sys
sys.path.insert(0, ".")

errors = []

def check(desc, condition):
    if condition:
        print(f"  [PASS] {desc}")
    else:
        print(f"  [FAIL] {desc}")
        errors.append(desc)

print("=" * 60)
print("  eComBot Comprehensive Check")
print("=" * 60)

# Multi-Agent Orchestration
print("\n--- Multi-Agent Orchestration ---")

from src.agents.orchestrator import orchestrator_agent, delegation_trace, get_delegation_trace, clear_delegation_trace
check("Orchestrator agent created", orchestrator_agent is not None)
check("Orchestrator name correct", orchestrator_agent.name == "ecombot_orchestrator")
check("Orchestrator has 2 tools", len(orchestrator_agent.tools) == 2)
check("delegation_trace is list", isinstance(delegation_trace, list))

from src.agents.support_agent import support_agent
check("Support agent created", support_agent is not None)
check("Support agent name", support_agent.name == "ecombot_support")
check("Support has order tools", any(t.__name__ == "get_order_status" for t in support_agent.tools))
check("Support has cancel tool", any(t.__name__ == "cancel_order" for t in support_agent.tools))

from src.agents.sales_agent import sales_agent
check("Sales agent created", sales_agent is not None)
check("Sales agent name", sales_agent.name == "ecombot_sales")
check("Sales has lookup_product", any(t.__name__ == "lookup_product" for t in sales_agent.tools))
check("Sales has check_stock", any(t.__name__ == "check_stock" for t in sales_agent.tools))

from agent import root_agent
check("root_agent is orchestrator", root_agent.name == "ecombot_orchestrator")

# Chainlit UI
print("\n--- Chainlit UI ---")

import chainlit as cl
check("Chainlit importable", cl is not None)
check("Chainlit version >= 2.0", cl.__version__.split(".")[0] >= "2")

from src.ui.chainlit_app import on_chat_start, on_message
check("on_chat_start defined", callable(on_chat_start))
check("on_message defined", callable(on_message))

# Voice Pipeline
print("\n--- Voice Pipeline ---")

from src.voice.stt_openrouter import transcribe
check("STT transcribe function", callable(transcribe))

from src.voice.tts_openrouter import synthesize, synthesize_streaming
check("TTS synthesize function", callable(synthesize))
check("TTS streaming function", callable(synthesize_streaming))

from src.voice.audio_io import AudioIO
check("AudioIO class exists", AudioIO is not None)
aio = AudioIO(enable_barge_in=False)
check("AudioIO instantiates", aio is not None)

from src.voice.metrics import VoiceMetrics, print_metrics_table
check("VoiceMetrics class", VoiceMetrics is not None)
m = VoiceMetrics()
t = m.start_turn()
check("Metrics start_turn works", t is not None)
m.end_turn()
check("Metrics end_turn works", len(m.turns) == 1)

from src.voice.languages import get_language, LANGUAGES
check("3 languages defined", len(LANGUAGES) == 3)
check("English config", get_language("en").name == "English")
check("French config", get_language("fr").name == "Français")
check("Hindi config", get_language("hi").name == "हिन्दी")

from src.voice.pipeline import VoicePipeline
check("VoicePipeline class", VoicePipeline is not None)
vp = VoicePipeline(language="en", text_mode=True)
check("VoicePipeline instantiates (text mode)", vp is not None)
check("VoicePipeline has metrics", vp.metrics is not None)

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"  FAILED: {len(errors)} check(s)")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ALL CHECKS PASSED!")
print("=" * 60)
