from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional
import logging
from .prompt import BEHOLD_AGENT_PROMPT
from .tools import (
    fetch_shopify_graphql,
    validate_graphql_with_mcp,
    introspect_graphql_schema,
    fetch_shopify_storefront_graphql,
    execute_shopify_operation,
    get_store_info,
    send_whatsapp_message,
    send_whatsapp_image,
    get_whatsapp_client_info,
    check_whatsapp_status,
    get_whatsapp_qr_info,
    start_whatsapp_bridge,
)

logger = logging.getLogger(__name__)


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed before agent starts processing.
    Sets up state for message tracking.
    """
    # Initialize message tracking in state if not present
    if "messages" not in callback_context.state:
        callback_context.state["messages"] = []
    
    logger.debug(f"Before agent callback - Current messages in state: {len(callback_context.state['messages'])}")
    
    # Return None to allow normal agent execution
    return None


def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed after agent completes processing.
    Saves the latest user message and assistant response to state.
    """
    try:
        # Get the current invocation context to access the session
        session = callback_context._invocation_context.session
        
        # Get current messages from state
        messages = callback_context.state.get("messages", [])
        
        # Find the latest user message and assistant response from session events
        latest_user_message = None
        latest_assistant_response = None
        
        # Look through session events for the most recent user and assistant messages
        for event in reversed(session.events):
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'role'):
                    if event.content.role == "user" and latest_user_message is None:
                        # Extract text from user message
                        user_text = ""
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                user_text += part.text
                        latest_user_message = user_text
                    elif event.content.role == "model" and latest_assistant_response is None:
                        # Extract text from assistant response
                        assistant_text = ""
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                assistant_text += part.text
                        latest_assistant_response = assistant_text
        
        # If we found both messages, save them to state
        if latest_user_message and latest_assistant_response:
            message_pair = {
                "user_message": latest_user_message,
                "assistant_response": latest_assistant_response,
                "timestamp": session.events[-1].timestamp if session.events else None
            }
            
            messages.append(message_pair)
            callback_context.state["messages"] = messages
            
            logger.info(f"✅ Message pair saved to state. Total messages: {len(messages)}")
        else:
            logger.debug(f"Could not find complete message pair - User: {bool(latest_user_message)}, Assistant: {bool(latest_assistant_response)}")
            
    except Exception as e:
        logger.error(f"❌ Failed to save messages in after_agent_callback: {e}")
    
    # Return None to use the original agent output
    return None


root_agent = Agent(
    model="gemini-2.5-flash",
    name="behold_agent",
    description=(
        "Intelligent Shopify sales assistant that proactively helps customers by automatically accessing store data "
        "to provide product recommendations, answer questions, guide purchasing decisions, manage carts, create checkouts, "
        "and calculate shipping fees."
    ),
    instruction=(BEHOLD_AGENT_PROMPT),
    tools=[
        # Core GraphQL tools
        fetch_shopify_graphql,
        fetch_shopify_storefront_graphql,
        validate_graphql_with_mcp,
        introspect_graphql_schema,

        # Universal operation tool
        execute_shopify_operation,

        # Store discovery tool
        get_store_info,

        # WhatsApp communication tools
        send_whatsapp_message,
        send_whatsapp_image,
        get_whatsapp_client_info,
        check_whatsapp_status,
        get_whatsapp_qr_info,
        start_whatsapp_bridge,
    ],
    # ADK callbacks for automatically saving messages to state
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)
