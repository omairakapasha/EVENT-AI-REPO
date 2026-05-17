"""OrchestratorAgent — coordinates multi-step flows."""
from agents import Agent
from pipeline.instructions import ORCHESTRATOR_INSTRUCTIONS
from tools import search_vendors, check_vendor_availability, compare_vendors


def build_orchestrator_agent(model, event_planner, vendor_discovery, booking):
    return Agent(
        name="OrchestratorAgent",
        model=model,
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        tools=[search_vendors, check_vendor_availability, compare_vendors],
        handoffs=[event_planner, vendor_discovery, booking],
    )
