import sys
sys.path.insert(0, ".")

print("Testing agent imports...")
from src.agents.orchestrator import orchestrator_agent, get_delegation_trace, delegate_to_support_agent, delegate_to_sales_agent
from src.agents.sales_agent import sales_agent
from src.agents.support_agent import support_agent
print("  OK: Orchestrator, Sales Agent, Support Agent")

print("Testing Chainlit imports...")
import chainlit
print(f"  OK: Chainlit v{chainlit.__version__}")

print("Testing Voice imports...")
from src.voice.stt_openrouter import transcribe
from src.voice.tts_openrouter import synthesize, synthesize_streaming
from src.voice.metrics import VoiceMetrics, print_metrics_table
from src.voice.languages import get_language, LANGUAGES
from src.voice.pipeline import VoicePipeline
print("  OK: Voice pipeline (STT, TTS, Metrics, Languages)")

print("Testing agent.py root_agent...")
from agent import root_agent
print(f"  OK: root_agent = {root_agent.name}")

print()
print("All modules import successfully!")
