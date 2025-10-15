# Analytics & Business Intelligence System

Complete sales attribution and business intelligence for the Behold Shopify Agent.

## 🎯 Features

### 1. **Complete Order Attribution**
- Tags all carts created by the agent with conversation metadata
- Shopify webhooks link completed orders back to agent conversations
- Track exactly which sales came from the agent

### 2. **Business Intelligence Dashboard**
- **Overview Metrics**: Total revenue, conversion rates, order counts
- **Revenue Analytics**: Daily revenue breakdown, average order value
- **Product Performance**: Top products by views, cart adds, and purchases
- **Conversion Funnel**: Track user journey from message to purchase
- **Agent Performance**: Action success rates, response times
- **User Engagement**: Active users, repeat customers, session duration

### 3. **Event Tracking**
- Every agent action logged (searches, cart creates, product views)
- Complete conversation history with message tracking
- Performance metrics (response times, success rates)

## 📊 Architecture

### Database Models
- **User**: WhatsApp users interacting with the agent
- **Conversation**: Conversation sessions with metrics
- **Message**: Individual messages (user + assistant)
- **AgentAction**: Every tool call the agent makes
- **Cart**: Carts created with attribution metadata
- **Order**: Completed orders from Shopify webhooks
- **ProductView**: Products viewed/recommended

### Key Components
1. **database.py**: SQLAlchemy models and database manager
2. **tracking_service.py**: High-level API for logging events
3. **cart_attribution.py**: Cart tagging for order attribution
4. **webhook_handler.py**: Shopify webhook processing
5. **analytics_service.py**: BI queries and metrics generation
6. **api_routes.py**: REST API endpoints for dashboard

## 🚀 Quick Start

### 1. Environment Setup

Add to your `.env`:

```env
# Database (defaults to SQLite for development)
DATABASE_URL=sqlite:///./behold_analytics.db

# For production, use PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# Shopify Webhook Secret (from Shopify Admin)
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret_here

# Your app's public URL (for webhook registration)
APP_URL=https://your-app.com
```

### 2. Install Dependencies

```bash
uv install
```

This installs:
- `sqlalchemy>=2.0.0` - Database ORM
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter

### 3. Initialize Database

The database is automatically initialized on app startup. Tables are created from models.

### 4. Set Up Shopify Webhooks

#### Via Shopify Admin:
1. Go to: **Settings → Notifications → Webhooks**
2. Click **"Create webhook"**
3. Configure:
   - **Event**: Order creation
   - **Format**: JSON
   - **URL**: `https://your-app.com/webhooks/shopify/orders/create`
   - **API Version**: 2025-01 or latest

4. Save and copy the **Webhook Secret**
5. Add to `.env` as `SHOPIFY_WEBHOOK_SECRET`

#### Via API (get setup instructions):
```bash
GET /analytics/setup/webhooks
```

## 📡 API Endpoints

### Analytics Endpoints

#### Overview Metrics
```bash
GET /analytics/overview?days=30
```
Response:
```json
{
  "period": {"start_date": "2025-01-01", "end_date": "2025-01-31"},
  "conversations": {
    "total": 150,
    "unique_users": 120,
    "total_messages": 450
  },
  "commerce": {
    "carts_created": 45,
    "orders_completed": 12,
    "total_revenue": 3450.00,
    "avg_order_value": 287.50
  },
  "conversion": {
    "cart_to_order_rate": 26.67,
    "conversation_to_order_rate": 8.00
  }
}
```

#### Daily Revenue
```bash
GET /analytics/revenue/daily?days=30
```

#### Top Products
```bash
GET /analytics/products/top?limit=10
```

#### Conversion Funnel
```bash
GET /analytics/funnel?days=30
```

#### Agent Performance
```bash
GET /analytics/agent/performance?days=30
```

#### User Engagement
```bash
GET /analytics/users/engagement?days=30
```

### Webhook Endpoints

#### Order Creation (Shopify webhook)
```bash
POST /webhooks/shopify/orders/create
```
Receives order creation events from Shopify and attributes them to agent conversations.

## 🔧 Integration Guide

### Step 1: Track Agent Actions

When the agent performs any action, log it:

```python
from analytics import tracking_service

# Example: Product search
tracking_service.record_agent_action(
    conversation_id="session_123",
    action_type="search_products",
    parameters={"query": "shoes", "limit": 10},
    result={"products": [...], "count": 5},
    success=True,
    execution_time_ms=150
)
```

### Step 2: Record Cart Creation with Attribution

The cart creation functions already include attribution. Make sure to pass context:

```python
# In shopify_tool.py
_execute_cart_creation(
    lines=[...],
    conversation_id="session_123",  # Pass this
    user_id="whatsapp_user_456"     # Pass this
)
```

### Step 3: Track Product Views

When showing products to users:

```python
tracking_service.record_product_view(
    conversation_id="session_123",
    product_id="gid://shopify/Product/123",
    product_title="Red Sneakers",
    product_price=89.99,
    product_type="Shoes",
    recommended_by_agent=True
)
```

### Step 4: Start/End Conversations

```python
# Start conversation
tracking_service.start_conversation(
    conversation_id="session_123",
    user_id="whatsapp_user_456"
)

# Record messages
tracking_service.record_message(
    conversation_id="session_123",
    role="user",
    content="Show me shoes"
)

# End conversation (optional - useful for duration tracking)
tracking_service.end_conversation("session_123")
```

## 📈 Business Intelligence Queries

### Most Common Use Cases:

**1. Total Agent-Attributed Revenue**
```python
result = analytics_service.get_overview_metrics(start_date, end_date)
revenue = result["commerce"]["total_revenue"]
```

**2. Best-Selling Products**
```python
products = analytics_service.get_top_products(limit=10, start_date, end_date)
for product in products:
    print(f"{product['product_title']}: {product['purchases']} sales")
```

**3. Conversion Rate by Stage**
```python
funnel = analytics_service.get_conversion_funnel(start_date, end_date)
for stage in funnel["funnel_stages"]:
    print(f"{stage['stage']}: {stage['percentage']}%")
```

**4. Agent Effectiveness**
```python
performance = analytics_service.get_agent_performance_metrics(start_date, end_date)
success_rate = performance["actions"]["success_rate"]
```

## 🔒 Security Considerations

### Webhook Verification
All Shopify webhooks are verified using HMAC-SHA256:
```python
# Automatically handled in webhook_handler.py
verify_shopify_webhook(body, hmac_header, secret)
```

### Database Security
- Use environment variables for database credentials
- Enable SSL for PostgreSQL connections in production
- Implement connection pooling for performance

### API Security (Recommended Additions)
Consider adding:
- API key authentication for analytics endpoints
- Rate limiting
- IP whitelisting for production

## 🎨 Dashboard Ideas

Build a merchant dashboard using the analytics API:

**Suggested Charts:**
1. **Revenue Over Time** (line chart from `/analytics/revenue/daily`)
2. **Conversion Funnel** (funnel chart from `/analytics/funnel`)
3. **Top Products** (bar chart from `/analytics/products/top`)
4. **Key Metrics Cards** (from `/analytics/overview`)
5. **Agent Performance** (gauge charts from `/analytics/agent/performance`)

**Frontend Stack Suggestions:**
- React/Next.js + Chart.js
- Vue.js + ApexCharts
- Streamlit (Python-based, quickest)

## 🧪 Testing

### Manual Testing

1. **Test Cart Attribution**:
```bash
# Create a cart through the agent
# Check database for attribution tags
SELECT id, conversation_id, user_id FROM carts;
```

2. **Test Webhook**:
```bash
# Use Shopify's webhook test feature
# Or send a test payload via curl
curl -X POST http://localhost:8000/webhooks/shopify/orders/create \
  -H "Content-Type: application/json" \
  -d @test_order.json
```

3. **Test Analytics**:
```bash
# Query overview
curl http://localhost:8000/analytics/overview?days=7

# Query top products
curl http://localhost:8000/analytics/products/top?limit=5
```

## 📝 Database Migrations

For schema changes, consider using Alembic:

```bash
# Install
uv add alembic

# Initialize
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

## 🐛 Troubleshooting

**Q: Orders not being attributed?**
- Check `SHOPIFY_WEBHOOK_SECRET` is set correctly
- Verify webhook is registered in Shopify Admin
- Check logs for webhook processing errors
- Ensure cart attribution is enabled in cart creation

**Q: Database errors?**
- Verify `DATABASE_URL` is correct
- Check database permissions
- Ensure database exists (for PostgreSQL)

**Q: Analytics returning zero results?**
- Check date ranges (might be no data in that period)
- Verify tracking service is being called
- Check database for data: `SELECT COUNT(*) FROM conversations;`

## 🚀 Production Checklist

- [ ] Set up PostgreSQL database
- [ ] Configure `DATABASE_URL` with production credentials
- [ ] Register Shopify webhook with production URL
- [ ] Set `SHOPIFY_WEBHOOK_SECRET`
- [ ] Enable database backups
- [ ] Set up monitoring/alerting for webhook failures
- [ ] Configure CORS properly in main.py
- [ ] Add API authentication for analytics endpoints
- [ ] Set up database connection pooling
- [ ] Enable SQL query logging only in debug mode

## 📚 Additional Resources

- [Shopify Webhooks Documentation](https://shopify.dev/docs/api/admin-rest/latest/resources/webhook)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
