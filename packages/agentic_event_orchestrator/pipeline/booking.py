"""BookingAgent — manages booking requests with tool-level guardrails."""
from agents import Agent, function_tool
from agents.run_context import RunContextWrapper
from pipeline.instructions import BOOKING_INSTRUCTIONS
from services.agent_context import AgentContext
from services.guardrail_hooks import tool_injection_guard, tool_pii_redact
from tools import get_my_bookings, get_booking_details, cancel_booking, get_vendor_services
from tools import get_active_quotes, submit_counter_offer
from tools.booking_tools import create_booking_request as _raw_create_booking

import json


@function_tool(
    tool_input_guardrails=[tool_injection_guard],
    tool_output_guardrails=[tool_pii_redact],
)
async def create_booking_request(
    ctx: RunContextWrapper[AgentContext],
    vendor_id: str,
    service_id: str,
    event_date: str,
    event_name: str,
    guest_count: int,
    notes: str = "",
    quantity: int = 1,
) -> str:
    """Create a booking inquiry request for a vendor service.
    IMPORTANT: Only call this AFTER showing the user a summary and receiving explicit confirmation.
    Returns a JSON string with booking_id and status."""
    # Delegate to the raw tool's underlying function via its on_invoke_tool,
    # passing the context and a JSON string of the arguments.
    return await _raw_create_booking.on_invoke_tool(
        ctx,
        json.dumps({
            "vendor_id": vendor_id,
            "service_id": service_id,
            "event_date": event_date,
            "event_name": event_name,
            "guest_count": guest_count,
            "notes": notes,
            "quantity": quantity,
        }),
    )


def build_booking_agent(model):
    return Agent(
        name="BookingAgent",
        model=model,
        instructions=BOOKING_INSTRUCTIONS,
        tools=[
            create_booking_request,
            get_my_bookings, get_booking_details, cancel_booking,
            get_vendor_services,
            get_active_quotes, submit_counter_offer,
        ],
    )

