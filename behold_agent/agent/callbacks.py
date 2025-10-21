"""
Agent callbacks for conversation state management.

This module contains the before and after agent callbacks that handle
automatic saving of conversation messages to the agent's state.
"""

from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed before agent starts processing.
    Sets up state for message tracking.
    """
    logger.info("🚀 Before agent callback triggered - Initializing message tracking")
    
    # Diagnostic logging for invocation state
    invocation_context = callback_context._invocation_context
    logger.info(f"🔍 Invocation context state: end_invocation={getattr(invocation_context, 'end_invocation', 'N/A')}")
    logger.info(f"🔍 Session ID: {getattr(invocation_context.session, 'id', 'N/A')}")
    logger.info(f"🔍 Current session events count: {len(getattr(invocation_context.session, 'events', []))}")
    
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
    logger.info("🔄 After agent callback triggered - Starting message processing")
    
    # Diagnostic logging for invocation state
    invocation_context = callback_context._invocation_context
    logger.info(f"🔍 After callback - end_invocation={getattr(invocation_context, 'end_invocation', 'N/A')}")
    logger.info(f"🔍 After callback - Session events count: {len(getattr(invocation_context.session, 'events', []))}")
    
    try:
        # Get the current invocation context to access the session
        logger.info("📋 Getting session from invocation context...")
        session = callback_context._invocation_context.session
        logger.info(f"📊 Session accessed successfully - ID: {session.id}")
        
        # Get current messages from state
        logger.info("💾 Accessing state messages...")
        messages = callback_context.state.get("messages", [])
        logger.info(f"💾 Current messages in state: {len(messages)}")
        
        # Find the latest user message and assistant response from session events
        latest_user_message = None
        latest_assistant_response = None
        
        logger.info(f"🔍 Starting to parse {len(session.events)} session events...")
        
        # Look through session events for the most recent user and assistant messages
        for i, event in enumerate(reversed(session.events)):
            logger.debug(f"📄 Processing event {i}: {type(event).__name__}")
            
            try:
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'role'):
                        role = event.content.role
                        logger.debug(f"📄 Event {i} has role: {role}")
                        
                        if role == "user" and latest_user_message is None:
                            # Extract text from user message
                            user_text = ""
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    user_text += part.text
                            
                            # Extract the actual user message from metadata wrapper
                            if user_text.strip():
                                # Look for [CURRENT USER MESSAGE] section
                                if "[CURRENT USER MESSAGE]" in user_text:
                                    actual_message = user_text.split("[CURRENT USER MESSAGE]")[-1].strip()
                                    if actual_message:
                                        latest_user_message = actual_message
                                        logger.info(f"👤 Found user message: {actual_message[:100]}...")
                                        logger.debug(f"👤 User message length: {len(actual_message)} chars")
                                    else:
                                        logger.debug(f"👤 User message after extraction was empty")
                                else:
                                    # Fallback: use the whole message if no wrapper found
                                    latest_user_message = user_text.strip()
                                    logger.info(f"👤 Found user message (no wrapper): {user_text[:100]}...")
                                    logger.debug(f"👤 User message length: {len(user_text)} chars")
                            else:
                                logger.debug(f"👤 User message was empty or whitespace only - raw: '{user_text}'")
                            
                        elif role == "model" and latest_assistant_response is None:
                            # Extract text from assistant response (skip function calls)
                            assistant_text = ""
                            has_text_content = False
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    assistant_text += part.text
                                    has_text_content = True
                                # Skip function calls - we only want final text responses
                                elif hasattr(part, 'function_call'):
                                    logger.debug(f"🔧 Skipping function call: {part.function_call.name}")
                                    continue
                            
                            # Only set if we got actual text content (not just function calls)
                            if has_text_content and assistant_text.strip():
                                latest_assistant_response = assistant_text.strip()
                                logger.info(f"🤖 Found assistant response: {assistant_text[:100]}...")
                                logger.debug(f"🤖 Assistant response length: {len(assistant_text)} chars")
                            else:
                                logger.debug(f"🤖 Assistant response was function call only or empty")
            except Exception as event_error:
                logger.warning(f"⚠️ Error processing event {i}: {event_error}")
                continue
        
        logger.info(f"🔍 Event parsing completed. Found user: {bool(latest_user_message)}, assistant: {bool(latest_assistant_response)}")
        
        # If we found both messages, save them to state
        if latest_user_message and latest_assistant_response:
            logger.info("💬 Creating message pair...")
            try:
                message_pair = {
                    "user_message": latest_user_message,
                    "assistant_response": latest_assistant_response,
                    "timestamp": session.events[-1].timestamp if session.events else None
                }
                
                logger.info("💾 Appending message pair to state...")
                messages.append(message_pair)
                callback_context.state["messages"] = messages
                
                logger.info(f"✅ Message pair saved to state. Total messages: {len(messages)}")
            except Exception as save_error:
                logger.error(f"❌ Error saving message pair: {save_error}")
        else:
            logger.warning(f"⚠️ Could not find complete message pair - User: {bool(latest_user_message)}, Assistant: {bool(latest_assistant_response)}")
            
    except Exception as e:
        logger.error(f"❌ Failed to save messages in after_agent_callback: {e}", exc_info=True)
    
    logger.info("🏁 After agent callback completed")
    # Return None to use the original agent output
    return None
