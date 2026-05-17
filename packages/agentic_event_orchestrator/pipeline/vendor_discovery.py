"""VendorDiscoveryAgent — searches vendor marketplace."""
from agents import Agent
from pipeline.instructions import VENDOR_DISCOVERY_INSTRUCTIONS
from tools import (
    search_vendors,
    get_vendor_details,
    get_vendor_recommendations,
    check_vendor_availability,
    get_vendor_services,
    compare_vendors,
)


def build_vendor_discovery_agent(model, booking=None):
    return Agent(
        name="VendorDiscoveryAgent",
        model=model,
        instructions=VENDOR_DISCOVERY_INSTRUCTIONS,
        tools=[
            search_vendors,
            get_vendor_details,
            get_vendor_recommendations,
            check_vendor_availability,
            get_vendor_services,
            compare_vendors,
        ],
        handoffs=[booking] if booking else [],
    )
