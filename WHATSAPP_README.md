# 📱 Behold WhatsApp Integration

Transform your Shopify agent into a powerful WhatsApp e-commerce assistant! This integration enables customers to shop, browse products, manage carts, and complete purchases directly through WhatsApp.

## ✨ Features

🛍️ **Complete Shopping Experience**
- Browse and search products via natural conversation
- Add items to cart with interactive buttons
- Real-time cart management and updates
- Secure checkout link generation
- Shipping cost calculations
- Store policy information

💬 **Rich WhatsApp Integration**
- Interactive buttons and lists
- Product carousels with images
- Cart summaries with pricing
- Personalized conversation history
- Multi-session user management
- Emoji-rich, mobile-optimized formatting

🚀 **Production Ready**
- Scalable webhook server with FastAPI
- Persistent session management
- Comprehensive error handling
- Docker deployment support
- Health monitoring and logging
- Rate limiting and security

## 🏗️ Architecture

```
WhatsApp User → Meta Cloud API → Webhook Server → Behold Agent → Shopify APIs
                                      ↓
                Message Formatter ← Session Manager
```

**Key Components:**
- **WhatsApp Server**: FastAPI webhook server
- **Message Handler**: Routes and processes messages  
- **Session Manager**: Manages conversation state
- **Formatters**: Convert responses to WhatsApp format
- **WhatsApp Client**: Sends rich messages via Meta API

## 🚀 Quick Start

### 1. Prerequisites
- Existing Behold Shopify agent (configured and working)
- Meta Developer account
- WhatsApp Business account
- Domain with HTTPS (for production)

### 2. Install Dependencies
```bash
pip install -r requirements-whatsapp.txt
```

### 3. Configure Environment
```bash
cp env.example .env
# Edit .env with your WhatsApp and Shopify credentials
```

### 4. Run the Server
```bash
python run_whatsapp.py
```

### 5. Setup Meta Webhook
1. Use ngrok for local testing: `ngrok http 8000`
2. Configure webhook in Meta Developer Console
3. Set webhook URL to: `https://your-url.ngrok.io/webhook`

## 📋 Setup Guides

- **📖 [Complete Setup Guide](WHATSAPP_SETUP.md)** - Step-by-step instructions
- **🏗️ [Architecture Overview](ARCHITECTURE.md)** - Technical architecture details

## 🔧 Configuration

### Basic Configuration
```bash
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Your existing Shopify config
SHOPIFY_STORE=your_store
SHOPIFY_ADMIN_TOKEN=your_admin_token
SHOPIFY_STOREFRONT_TOKEN=your_storefront_token
```

### Advanced Options
- **Session Storage**: File, PostgreSQL, or Redis
- **Rate Limiting**: Configurable per-user limits
- **Logging**: Multiple levels and outputs
- **Caching**: Redis for high-performance deployments

## 🐳 Docker Deployment

### Quick Deploy
```bash
docker-compose up -d
```

### Production Deploy
```bash
# With Redis and PostgreSQL
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 💬 User Experience

**Customer Journey:**
1. **Discovery**: "Show me running shoes"
2. **Browsing**: Interactive product lists with prices
3. **Selection**: Tap buttons to view details or add to cart  
4. **Cart Management**: Real-time cart updates and totals
5. **Checkout**: Secure Shopify checkout links
6. **Support**: Store policies and shipping info

**Example Conversation:**
```
Customer: Hi, I'm looking for sneakers
Bot: 👋 Welcome! I found 15 sneakers for you:

🏷️ *Nike Air Max 90* - $120
   Classic comfort and style
   ✅ In Stock

🏷️ *Adidas Ultraboost* - $180  
   Maximum energy return
   ✅ In Stock

[View Nike] [View Adidas] [More Options]

Customer: [taps "View Nike"]
Bot: 👟 *Nike Air Max 90* - $120

🏪 Brand: Nike
ℹ️ Category: Athletic Footwear

Classic Air Max cushioning with updated style...

✅ In Stock - Ready to ship!

[Add to Cart] [View Sizes] [Keep Browsing]
```

## 🔐 Security Features

- **HTTPS Required**: All webhook communication encrypted
- **Token Authentication**: Meta access token validation
- **Input Sanitization**: All user inputs cleaned and validated
- **Session Isolation**: User sessions completely isolated
- **Rate Limiting**: Configurable abuse prevention

## 📊 Monitoring

### Health Checks
```bash
curl https://your-domain.com/health
```

### Metrics Available
- Message volume and response times
- User engagement and conversion rates  
- Error rates by type and component
- Session duration and user retention

## 🛠️ Troubleshooting

**Common Issues:**

❌ **Webhook not receiving messages**
- Check webhook URL is HTTPS
- Verify WHATSAPP_VERIFY_TOKEN matches Meta config
- Ensure server is accessible from internet

❌ **Agent not responding**  
- Verify Shopify credentials in .env
- Check agent configuration in behold_agent/
- Review server logs for errors

❌ **Messages not sending**
- Verify WHATSAPP_ACCESS_TOKEN is valid
- Check phone number is added to test list
- Ensure API rate limits not exceeded

### Debug Commands
```bash
# Check server health
curl http://localhost:8000/health

# View logs
tail -f whatsapp_bot.log

# Test message sending
curl -X POST http://localhost:8000/send-message \
  -H "Content-Type: application/json" \
  -d '{"to": "1234567890", "message": "Test"}'
```

## 🎯 What's Next?

**Immediate Use:**
✅ Complete WhatsApp shopping experience  
✅ Natural conversation interface  
✅ Interactive product browsing  
✅ Secure checkout process  

**Future Enhancements:**
- 📊 Analytics dashboard
- 🌍 Multi-language support  
- 🤖 Enhanced AI features
- 📱 Rich media support
- 🔗 Social commerce features

## 📚 Documentation

- **[Setup Guide](WHATSAPP_SETUP.md)** - Complete setup instructions
- **[Architecture](ARCHITECTURE.md)** - Technical architecture details
- **[Original Agent Features](FEATURES.md)** - Your existing agent capabilities

## 🆘 Support

1. **Check Documentation**: Start with setup guide and architecture docs
2. **Review Logs**: Check application logs for error details  
3. **Meta Documentation**: [WhatsApp Business API docs](https://developers.facebook.com/docs/whatsapp)
4. **Community**: Join WhatsApp Business API developer community

---

## 🎉 Ready to Launch!

Your Shopify agent is now a complete WhatsApp e-commerce solution! Customers can discover products, manage carts, and complete purchases entirely through WhatsApp messaging.

**What your customers can now do:**
- 💬 Chat naturally to find products
- 🛍️ Browse with interactive buttons  
- 🛒 Manage shopping carts in real-time
- 💳 Get secure checkout links
- 🚚 Check shipping costs instantly
- ℹ️ Get store information and policies

**Scale with confidence:**
- 🔄 Handles thousands of concurrent users
- 📊 Built-in monitoring and health checks
- 🐳 Docker deployment ready
- 🔒 Production security standards
- 📈 Easy horizontal scaling

Transform every WhatsApp conversation into a potential sale! 🚀

