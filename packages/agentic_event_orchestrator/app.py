import chainlit as cl
from agents.sdk_agents import run_orchestration, run_vendor_discovery
from nlp_processor.structured_output import EventRequirements
import json

@cl.on_chat_start
async def start():
    await cl.Message(content="""
🎉 **Welcome to the Agentic Event Orchestrator!**

I can help you plan events using AI-powered agents. Just describe your event in natural language.

**Example:** "I want to plan a wedding for 200 people in Lahore on March 15th with a budget of PKR 500,000"

Our system uses specialized agents for:
- 🔍 Vendor Discovery
- 📅 Schedule Optimization
- ✅ Approval Workflow
- 📧 Guest Communication

How can I help you plan your event today?
""").send()

@cl.on_message
async def main(message: cl.Message):
    await cl.Message(content="🔍 Processing your request through our agentic workflow...").send()
    
    try:
        # Use the orchestrator agent to handle the complete workflow
        result = run_orchestration(message.content)
        
        # Format and display the result
        response_text = f"""{result.final_output}

---
*Processed by: {result.last_agent.name}*
"""
        
        await cl.Message(content=response_text).send()
        
        # Check if this was a plan creation and ask for approval
        if hasattr(result, 'new_items') and any('plan' in str(item).lower() for item in result.new_items):
            res = await cl.AskActionMessage(
                content="Would you like to proceed with approval and booking?",
                actions=[
                    cl.Action(name="approve", value="approve", label="Approve & Book"),
                    cl.Action(name="modify", value="modify", label="Request Changes"),
                    cl.Action(name="reject", value="reject", label="Cancel"),
                ],
            ).send()
            
            if res and res.get("value") == "approve":
                await cl.Message(content="✅ Processing approval and booking...").send()
                # Trigger approval workflow
                approval_result = run_orchestration("Approve the plan and proceed with booking and invitations")
                await cl.Message(content=f"✅ {approval_result.final_output}").send()
            elif res and res.get("value") == "modify":
                await cl.Message(content="📝 Please describe what changes you'd like to make...").send()
            else:
                await cl.Message(content="❌ Plan cancelled. Let me know if you'd like to create a new one!").send()
            
    except Exception as e:
        await cl.Message(content=f"❌ An error occurred: {str(e)}").send()
