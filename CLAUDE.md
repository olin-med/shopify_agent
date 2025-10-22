# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WhatsApp Shopify sales agent** built with Google's Agent Development Kit (ADK) that provides intelligent customer assistance through WhatsApp. The agent can search products, manage carts, calculate shipping, and facilitate checkouts while tracking comprehensive business intelligence metrics.

## Development Commands

**Package Management:**
- `uv install` - Install dependencies using UV package manager
- `uv add package` - Add new dependencies
- `uv sync` - Sync dependencies with lock file

**Running the Application:**
- `python behold_agent/main.py` - Run the FastAPI server (default port 8080)
- `uvicorn behold_agent.main:app --reload` - Run with hot reload for development

**Docker:**
- `docker build -t behold-agent .` - Build Docker image (use Dockerfile in behold_agent/)
- `docker run -p 8080:8080 --env-file .env behold-agent` - Run containerized

## Architecture

### Core Components

**1. Main Application (`behold_agent/main.py`)**
- FastAPI server handling WhatsApp message processing
- Integrates Google ADK Runner for agent execution
- Session management and context tracking
- Analytics tracking integration
- Endpoints: `/process-whatsapp-message`, `/health`, `/stats`, `/analytics/*`

**2. Agent Configuration (`behold_agent/agent/agent.py`)**
- Uses Google ADK Agent class with `gemini-2.5-flash` model
- Configures 16 tools (6 Shopify core, 1 store discovery, 6 WhatsApp, 3 GraphQL utilities)
- Loads comprehensive instruction prompt from `prompt.py`

**3. Shopify Integration (`behold_agent/agent/tools/shopify_tool.py`)**
- **MCP Integration**: Uses Shopify's Model Context Protocol via `npx @shopify/dev-mcp@latest`
- **Universal Operation Tool**: `execute_shopify_operation(intent, parameters, api)` - handles operations via natural language intents
- **Fallback System**: Hardcoded GraphQL queries when MCP unavailable
- **Core Functions**: Product search, cart create/modify, shipping calculation, discount application
- **Order Attribution**: Automatically tags carts with `conversation_id` and `user_id` for analytics

**4. Session Context (`behold_agent/agent/session_context.py`)**
- Maintains 5-turn conversation window (10 messages: 5 user + 5 assistant)
- Thread-safe with asyncio.Lock for concurrent access
- Tracks: conversation history, current cart, product searches, shipping address, preferences
- Auto-cleanup of stale contexts (2 hour TTL)
- Context summaries injected into agent prompts for continuity

**5. WhatsApp Integration (`behold_agent/agent/tools/whatsapp/`)**
- `whatsapp_tool.py` - Core tools: send messages, send images, get client info, check status
- `whatsapp_integration.py` - Bridge connection management
- `webhook_handler.py` - Webhook processing for incoming messages
- Requires `WHATSAPP_BRIDGE_URL` environment variable

**6. Analytics System (`behold_agent/analytics/`)**
- Complete order attribution via Shopify webhooks
- Database models: User, Conversation, Message, AgentAction, Cart, Order, ProductView
- SQLAlchemy ORM with SQLite (dev) or PostgreSQL (production)
- Tracking service records: product views, cart operations, agent actions, messages
- BI queries: revenue, conversion funnel, product performance, agent effectiveness
- REST API at `/analytics/*` for dashboard integration

### Data Flow

1. WhatsApp message received at `/process-whatsapp-message`
2. User/conversation tracked in database (analytics)
3. Session context loaded (5-turn window)
4. Context summary + message + attribution IDs injected into agent prompt
5. Google ADK Runner executes agent with access to 16 tools
6. Agent uses Shopify tools (via MCP or fallback) to fulfill request
7. All actions tracked in analytics database
8. Response sent back (either via WhatsApp tools directly or returned to bridge)
9. Turn stored in session context for next interaction
10. Shopify webhooks attribute completed orders back to agent conversations

### Key Architectural Patterns

**Context Injection Pattern:**
The system injects three critical pieces into every agent prompt:
- `[USER WHATSAPP ID: {user_id}]` - For sending WhatsApp images
- `[CONVERSATION ID: {session_id}]` - For analytics tracking
- `[CONTEXT FROM PREVIOUS TURNS]` - For conversation continuity

**Attribution Pattern:**
Carts created by agent include custom attributes for order tracking:
```python
attributes = [
    {"key": "_agent_conversation_id", "value": session_id},
    {"key": "_agent_user_id", "value": user_id},
    {"key": "_agent_source", "value": "behold_whatsapp_agent"}
]
```

**MCP Fallback Pattern:**
All Shopify operations attempt MCP first, fall back to hardcoded queries:
1. Try `build_dynamic_query()` using MCP
2. On failure, call `_fallback_operation()` with hardcoded GraphQL
3. Return user-friendly error messages

**Tool Detection Pattern:**
Agent detects when WhatsApp tools are used and skips bridge response:
```python
if whatsapp_tool_used:
    return {"status": "success", "message": "Agent sent messages directly"}
else:
    return {"reply": response_text}  # Bridge sends this
```

## Environment Variables

Required in `.env`:

```env
# Google ADK
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Shopify Configuration
SHOPIFY_STORE=your-store-name
SHOPIFY_ADMIN_TOKEN=shpat_xxx
SHOPIFY_STOREFRONT_TOKEN=xxx
SHOPIFY_API_VERSION=2025-01
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret

# WhatsApp Bridge
WHATSAPP_BRIDGE_URL=http://bridge-url

# Server
HOST=0.0.0.0
PORT=8080
DEBUG=false

# Database (Analytics)
DATABASE_URL=sqlite:///./behold_analytics.db
# DATABASE_URL=postgresql://user:password@host:5432/dbname  # Production
```

## Dependencies

Key packages in `pyproject.toml`:
- **google-adk>=1.12.0** - Google Agent Development Kit
- **fastapi>=0.104.0**, **uvicorn[standard]>=0.24.0** - Web server
- **sqlalchemy>=2.0.0**, **psycopg2-binary>=2.9.9** - Database ORM
- **requests>=2.31.0** - HTTP client for Shopify GraphQL
- **python-dotenv>=1.0.0** - Environment variables
- **redis>=5.0.0** - Optional session storage (not actively used)

External dependencies:
- **Node.js + npx** - Required for Shopify MCP (`@shopify/dev-mcp`)

## Analytics & Business Intelligence

### Setup Shopify Webhooks

1. **Via Shopify Admin:**
   - Go to Settings → Notifications → Webhooks
   - Create webhook: Order creation → `https://your-app.com/webhooks/shopify/orders/create`
   - Copy webhook secret to `SHOPIFY_WEBHOOK_SECRET`

2. **Database Initialization:**
   - Automatic on app startup via `lifespan` manager
   - Tables created from SQLAlchemy models

### Key Analytics Endpoints

- `GET /analytics/overview?days=30` - Revenue, conversions, totals
- `GET /analytics/revenue/daily?days=30` - Daily revenue breakdown
- `GET /analytics/products/top?limit=10` - Best-selling products
- `GET /analytics/funnel?days=30` - Conversion funnel metrics
- `GET /analytics/agent/performance?days=30` - Agent effectiveness
- `GET /analytics/users/engagement?days=30` - User activity metrics

### Tracking Integration

Key tracking points in code:
- **Product searches** (`shopify_tool.py:924-960`) - Track all viewed products
- **Cart creation** (`shopify_tool.py:1064-1092`) - Track cart with attribution
- **Cart updates** (`shopify_tool.py:1254-1289`) - Track products added to cart
- **Messages** (`main.py:329-336`, `main.py:389-399`) - Track all conversation
- **Agent actions** (`main.py:401-437`) - Track all tool calls and results

## Testing & Validation

**Test Shopify connectivity:**
```python
from agent.tools.shopify_tool import get_store_info
result = get_store_info()
# Should return store name and product types
```

**Test session context:**
```bash
# Get context for user
curl http://localhost:8080/context/{user_id}

# Clear context
curl -X POST http://localhost:8080/clear-context/{user_id}

# System stats
curl http://localhost:8080/stats
```

**Test analytics:**
```bash
curl http://localhost:8080/analytics/overview?days=7
```

**Cleanup stale contexts:**
```bash
curl -X POST http://localhost:8080/cleanup-contexts
```

## Important Implementation Notes

1. **Session Management**: Google ADK sessions are separate from context manager. Sessions persist in InMemorySessionService, contexts in ContextManager (2hr TTL).

2. **Attribution Requirements**: Always pass `conversation_id` and `user_id` to Shopify operations for analytics tracking. These are injected into agent prompt but must be extracted and passed to tool functions.

3. **MCP Availability**: The system gracefully degrades when Node.js/npx unavailable. All operations have hardcoded fallbacks.

4. **Thread Safety**: `ContextManager` uses threading.Lock, `SessionContext` uses asyncio.Lock. Safe for concurrent users.

5. **Shipping Calculations**: Uses CartDelivery API with two-step process: (1) update buyer identity, (2) add delivery addresses. Country codes are normalized (e.g., "Brazil" → "BR").

6. **WhatsApp Tool Detection**: Agent can either use WhatsApp tools directly (sends via bridge) or return text (bridge sends). Detection happens in main.py by checking function_call.name.

7. **Image Support**: Agent must extract `[USER WHATSAPP ID: xxx]` from prompt to use `send_whatsapp_image()` tool correctly.

8. **Database Schema Changes**: Consider using Alembic for migrations if modifying analytics models.
