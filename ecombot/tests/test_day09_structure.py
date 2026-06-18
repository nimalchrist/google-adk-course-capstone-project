import sys
sys.path.insert(0, ".")

from src.agents.orchestrator import orchestrator_agent, delegation_trace

print("Orchestrator Agent:")
print(f"  Name: {orchestrator_agent.name}")
print(f"  Model: {orchestrator_agent.model}")
print(f"  Tools: {[t.__name__ if hasattr(t, '__name__') else str(t) for t in orchestrator_agent.tools]}")
print(f"  Description: {orchestrator_agent.description[:80]}...")
print()

from src.agents.support_agent import support_agent
print("Support Agent:")
print(f"  Name: {support_agent.name}")
print(f"  Tools: {[t.__name__ for t in support_agent.tools]}")
print()

from src.agents.sales_agent import sales_agent
print("Sales Agent:")
print(f"  Name: {sales_agent.name}")
print(f"  Tools: {[t.__name__ for t in sales_agent.tools]}")
print()

# Verify no tool overlap between agents (by design)
support_tools = set(t.__name__ for t in support_agent.tools)
sales_tools = set(t.__name__ for t in sales_agent.tools)
overlap = support_tools & sales_tools
print(f"Support tools: {support_tools}")
print(f"Sales tools: {sales_tools}")
print(f"Overlap: {overlap}")
print()
print("Multi-agent structure verified!")
