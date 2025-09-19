# Behold WhatsApp Integration Architecture

## 🏗️ System Architecture Overview

This document outlines the complete architecture of the Behold WhatsApp integration, showing how WhatsApp Business API connects with your existing Shopify agent.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WhatsApp      │    │  Meta WhatsApp  │    │   Your Webhook  │    │  Behold Agent   │
│     Users       │◄──►│   Cloud API     │◄──►│     Server      │◄──►│   (Google ADK)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │                        │
                                                        ▼                        ▼
                                               ┌─────────────────┐    ┌─────────────────┐
                                               │ Session Manager │    │  Shopify APIs   │
                                               │   & Storage     │    │ (Admin + Store) │
                                               └─────────────────┘    └─────────────────┘
```

## 📱 Component Overview

### 1. WhatsApp Integration Layer

#### **WhatsApp Server** (`whatsapp_server.py`)
- **Purpose**: FastAPI webhook server that receives WhatsApp messages
- **Responsibilities**:
  - Webhook verification for Meta
  - Message routing and processing
  - Health checks and monitoring
  - Background task management
- **Key Endpoints**:
  - `GET/POST /webhook` - Meta webhook
  - `GET /health` - Health monitoring
  - `POST /send-message` - Direct message sending (testing)

#### **WhatsApp Client** (`whatsapp/client.py`)
- **Purpose**: Handles outgoing messages to WhatsApp Business API
- **Features**:
  - Text messages with rich formatting
  - Interactive buttons and lists
  - Product carousels and cart summaries
  - Media messages (images, documents)
  - Message read receipts
- **API Integration**: Meta WhatsApp Business Cloud API v17.0

### 2. Session Management Layer

#### **Session Manager** (`whatsapp/session_manager.py`)
- **Purpose**: Manages user conversation state and history
- **Features**:
  - Persistent user sessions with file/database storage
  - Conversation state tracking (greeting, browsing, cart, checkout)
  - Message history (last 20 messages per user)
  - Shopping context (cart ID, last search, viewed products)
  - User profile management
  - Automatic session cleanup
- **Storage Options**:
  - File-based (default): JSON files in `data/sessions/`
  - PostgreSQL: For high-scale deployments
  - Redis: For session caching

#### **Session States**
```python
class ConversationState(Enum):
    GREETING = "greeting"
    BROWSING = "browsing"
    PRODUCT_INQUIRY = "product_inquiry"
    CART_MANAGEMENT = "cart_management"
    CHECKOUT_PROCESS = "checkout_process"
    SHIPPING_INQUIRY = "shipping_inquiry"
    POLICY_INQUIRY = "policy_inquiry"
    SUPPORT = "support"
    IDLE = "idle"
```

### 3. Message Processing Layer

#### **Message Handler** (`whatsapp/message_handler.py`)
- **Purpose**: Core message processing and agent integration
- **Responsibilities**:
  - Parse incoming WhatsApp messages (text, buttons, media)
  - Route messages to appropriate handlers
  - Integrate with Behold agent
  - Format agent responses for WhatsApp
  - Handle interactive responses (buttons, lists)
- **Message Types Supported**:
  - Text messages
  - Interactive button responses
  - List selections
  - Location sharing
  - Media files (images, documents, audio, video)

#### **Message Formatters** (`whatsapp/formatters.py`)
- **Purpose**: Convert agent responses to WhatsApp-friendly formats
- **Features**:
  - Product list formatting with prices and details
  - Cart summary with totals and line items
  - Shipping estimates with address details
  - Store policy information
  - Interactive button generation
  - Emoji integration and text cleanup
  - HTML tag removal and text truncation

### 4. Agent Integration Layer

#### **Behold Agent** (existing `behold_agent/`)
- **Purpose**: Your existing Google ADK Shopify agent
- **Capabilities**:
  - Product search and recommendations
  - Cart creation and management
  - Checkout link generation
  - Shipping calculations
  - Store policy retrieval
  - Complete e-commerce workflow

#### **Integration Bridge**
The message handler acts as a bridge between WhatsApp and your agent:

```python
# Prepare context for agent
agent_context = f"""
WhatsApp User Message: {user_message}

CONVERSATION CONTEXT:
{session.get_context_summary()}

INSTRUCTIONS:
- You are communicating via WhatsApp
- Keep responses concise but helpful
- Focus on shopping assistance
"""

# Call agent and format response
agent_response = await self._call_agent(agent_context)
formatted_response = self.formatter.format_agent_response(agent_response)
```

## 🔄 Message Flow Architecture

### Incoming Message Flow

```
1. User sends WhatsApp message
   ↓
2. Meta receives message
   ↓
3. Meta sends webhook to your server
   ↓
4. WhatsApp Server receives webhook
   ↓
5. Message Handler extracts message content
   ↓
6. Session Manager retrieves/creates user session
   ↓
7. Message Handler routes to appropriate processor
   ↓
8. Agent processes message and returns response
   ↓
9. Formatter converts response to WhatsApp format
   ↓
10. WhatsApp Client sends formatted response
    ↓
11. Session Manager updates conversation state
```

### Agent Response Processing

```
Agent Response → Response Parser → Format Detector → Formatter → WhatsApp API
      ↓              ↓               ↓                ↓            ↓
   Raw text     Extract data    Detect type     Apply format   Send message
                (products,      (product list,   (buttons,      (with rich
                 cart,           cart summary,    text,          formatting)
                 shipping)       shipping)        interactive)
```

## 🗃️ Data Architecture

### Session Data Structure

```json
{
  "phone_number": "+1234567890",
  "session_id": "whatsapp_1234567890_1234567890",
  "created_at": "2025-01-15T10:00:00Z",
  "last_activity": "2025-01-15T10:05:00Z",
  "conversation_state": "browsing",
  "user_name": "John Doe",
  "preferred_language": "en",
  "current_cart_id": "gid://shopify/Cart/123456789",
  "last_search_query": "running shoes",
  "last_product_viewed": "gid://shopify/Product/987654321",
  "message_history": [
    {
      "content": "Hi, I'm looking for shoes",
      "direction": "incoming",
      "type": "text",
      "timestamp": "2025-01-15T10:00:00Z"
    }
  ],
  "agent_context": {
    "last_action": "product_search",
    "preferences": {"category": "footwear"}
  }
}
```

### Message Types and Handling

| Message Type | Handler | Response Format |
|--------------|---------|-----------------|
| Text | `_process_message_content` | Formatted text + buttons |
| Button Reply | `_handle_interactive_response` | Context-specific action |
| List Selection | `_handle_interactive_response` | Context-specific action |
| Location | Location parser | Shipping calculation |
| Media | Media processor | Acknowledgment + action |

## 🔧 Configuration Architecture

### Environment Variables Structure

```bash
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=         # Meta access token
WHATSAPP_PHONE_NUMBER_ID=      # Phone number ID
WHATSAPP_VERIFY_TOKEN=         # Webhook verification

# Shopify Integration (existing)
SHOPIFY_STORE=                 # Store name
SHOPIFY_ADMIN_TOKEN=           # Admin API token
SHOPIFY_STOREFRONT_TOKEN=      # Storefront API token

# Server Configuration
HOST=0.0.0.0                   # Server host
PORT=8000                      # Server port
LOG_LEVEL=INFO                 # Logging level

# Storage Configuration
SESSION_STORAGE_PATH=data/sessions  # File storage path
SESSION_TIMEOUT_HOURS=24            # Session expiration
```

### Scalability Configuration

**File Storage** (Default - Single Server):
```bash
SESSION_STORAGE_PATH=data/sessions
```

**Database Storage** (Multi-Server):
```bash
DATABASE_URL=postgresql://user:pass@host/db
```

**Redis Caching** (High Performance):
```bash
REDIS_URL=redis://localhost:6379/0
```

## 🚀 Deployment Architecture

### Development Setup
```
Developer Machine
├── WhatsApp Server (localhost:8000)
├── ngrok tunnel (HTTPS exposure)
└── Meta webhook (points to ngrok URL)
```

### Production Setup
```
Production Environment
├── Load Balancer (SSL termination)
├── WhatsApp Server instances (multiple)
├── Redis cluster (session caching)
├── PostgreSQL (session persistence)
└── File storage/CDN (media files)
```

### Docker Architecture
```
Docker Network
├── whatsapp-bot (main application)
├── redis (session caching)
├── postgres (optional, session storage)
└── nginx (optional, reverse proxy)
```

## 🔐 Security Architecture

### Authentication Flow
1. **Webhook Verification**: Meta verifies webhook with token
2. **Token Validation**: Access tokens validated on each API call
3. **Session Security**: Sessions tied to phone numbers
4. **Input Validation**: All user inputs validated and sanitized

### Security Layers
- **Transport**: HTTPS for all webhook communication
- **Authentication**: Bearer token for WhatsApp API
- **Authorization**: Phone number-based session isolation
- **Input Sanitization**: HTML cleaning and content validation
- **Rate Limiting**: Configurable per-user rate limits

## 📊 Monitoring Architecture

### Health Checks
- **Application Health**: `/health` endpoint
- **Component Status**: All major components checked
- **External Dependencies**: WhatsApp API and Shopify API status

### Logging Structure
```
Logs/
├── Application logs (structured JSON)
├── Access logs (HTTP requests)
├── Error logs (exceptions and failures)
└── Session logs (user interactions)
```

### Metrics Collection
- Message volume and response times
- User engagement and conversion rates
- Error rates by type and component
- Resource utilization (CPU, memory, storage)

## 🔄 Integration Points

### WhatsApp ↔ Agent Integration
```python
class MessageHandler:
    async def _call_agent(self, context: str) -> str:
        # Integration point with Google ADK agent
        response = await self.agent.process(context)
        return response
```

### Agent ↔ Shopify Integration
```python
# Your existing agent tools
tools = [
    fetch_shopify_graphql,
    create_cart,
    search_products,
    calculate_shipping_estimate,
    # ... all your existing tools
]
```

## 🎯 Performance Architecture

### Async Processing
- All I/O operations are asynchronous
- Background tasks for webhook processing
- Non-blocking message handling

### Caching Strategy
- **Session Cache**: Redis for active sessions
- **Response Cache**: Common responses cached
- **Media Cache**: Product images and media

### Scalability Patterns
- **Horizontal Scaling**: Multiple server instances
- **Database Sharding**: Session data by phone number
- **Queue Processing**: Background task queues for heavy operations

## 🛠️ Extension Architecture

### Adding New Message Types
1. Extend `_extract_message_content` in MessageHandler
2. Add type-specific handlers
3. Update formatters for response types

### Adding New Agent Features
1. Add tools to your existing Behold agent
2. Update message parsing in MessageHandler
3. Add formatters for new response types

### Adding New Platforms
The architecture supports extending to other messaging platforms:
- Telegram: Replace WhatsApp client with Telegram client
- SMS: Add SMS client using Twilio
- Web Chat: Add WebSocket client for web integration

---

This architecture provides a robust, scalable foundation for WhatsApp e-commerce integration while maintaining clean separation of concerns and easy extensibility.

