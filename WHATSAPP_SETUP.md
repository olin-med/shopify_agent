# WhatsApp Business API Integration Setup Guide

This guide will walk you through setting up WhatsApp Business API integration for your Behold Shopify agent.

## 🚀 Quick Start

### Prerequisites

1. **Existing Behold Agent**: Your Shopify agent should already be configured and working
2. **Meta Developer Account**: Required for WhatsApp Business API
3. **WhatsApp Business Account**: Separate from personal WhatsApp
4. **Domain with HTTPS**: Required for production webhooks
5. **Python 3.8+**: For running the integration

### Architecture Overview

```
WhatsApp User → Meta Cloud API → Your Webhook Server → Behold Agent → Shopify APIs
                                        ↓
                WhatsApp Response ← Message Formatter ← Agent Response
```

## 📋 Step 1: Meta Developer Setup

### 1.1 Create Meta Developer Account

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Sign up or log in with your Facebook account
3. Complete the developer verification process

### 1.2 Create WhatsApp Business App

1. Go to [Meta for Developers Apps](https://developers.facebook.com/apps/)
2. Click "Create App"
3. Select "Business" as app type
4. Fill in app details:
   - **App Name**: "Behold Shopify Assistant"
   - **Contact Email**: Your email
   - **Business Account**: Select or create one

### 1.3 Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set up"
3. Select "Cloud API" (not On-Premises)

### 1.4 Get Your Credentials

After setting up WhatsApp, you'll get:

- **Temporary Access Token**: Copy this (valid for 24 hours)
- **Phone Number ID**: Copy this from the "From" dropdown
- **App ID** and **App Secret**: Found in App Settings

### 1.5 Generate Permanent Access Token

1. Go to WhatsApp > Getting Started
2. Click on your System User or create one
3. Generate a permanent access token with these permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`

## 📋 Step 2: Install Dependencies

### 2.1 Install WhatsApp Requirements

```bash
cd /path/to/your/behold/shopify_agent
pip install -r requirements-whatsapp.txt
```

### 2.2 Verify Existing Agent Dependencies

Make sure your existing agent dependencies are installed:

```bash
pip install -r behold_agent/pyproject.toml
```

## 📋 Step 3: Environment Configuration

### 3.1 Copy Environment Template

```bash
cp env.example .env
```

### 3.2 Configure Environment Variables

Edit your `.env` file with the credentials from Meta:

```bash
# WhatsApp Configuration
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_secure_random_string_here

# Your existing Shopify configuration
SHOPIFY_STORE=your_store_name
SHOPIFY_ADMIN_TOKEN=your_admin_token
SHOPIFY_STOREFRONT_TOKEN=your_storefront_token
SHOPIFY_API_VERSION=2025-07

# Server configuration
HOST=0.0.0.0
PORT=8000
```

**Important Notes:**
- **WHATSAPP_VERIFY_TOKEN**: Create a secure random string (use a password generator)
- Keep your `.env` file secure and never commit it to version control

## 📋 Step 4: Local Testing

### 4.1 Start the WhatsApp Server

```bash
python whatsapp_server.py
```

You should see:
```
INFO: Starting WhatsApp server on 0.0.0.0:8000
INFO: WhatsApp server initialized successfully
```

### 4.2 Test Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "whatsapp_client": true,
    "session_manager": true,
    "message_handler": true,
    "formatter": true
  }
}
```

### 4.3 Use ngrok for Local Testing

Install and run ngrok to expose your local server:

```bash
# Install ngrok (if not already installed)
npm install -g ngrok

# Expose your local server
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## 📋 Step 5: Configure Webhook in Meta

### 5.1 Set Webhook URL

1. Go to WhatsApp > Configuration in your Meta app
2. Click "Edit" next to Webhook
3. Set these values:
   - **Callback URL**: `https://your-ngrok-url.ngrok.io/webhook`
   - **Verify Token**: The same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`

### 5.2 Subscribe to Webhook Events

Check these webhook fields:
- ✅ `messages`
- ✅ `message_deliveries` (optional)
- ✅ `message_reads` (optional)

### 5.3 Verify Webhook

Click "Verify and Save". You should see a success message.

## 📋 Step 6: Test Your Integration

### 6.1 Get Test Phone Number

1. In WhatsApp > API Setup, find the test phone number
2. Add your personal phone number to the allowed list

### 6.2 Send Test Message

Send a WhatsApp message to the test number:
- **Message**: "Hi"
- **Expected Response**: Welcome message with menu buttons

### 6.3 Test Different Features

Try these commands:
- "Show me products"
- "What's in my cart?"
- "Help"
- Use the interactive buttons

## 🚀 Production Deployment

### Option 1: Simple VPS Deployment

1. **Get a VPS** (DigitalOcean, Linode, AWS EC2)
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip nginx certbot
   ```

3. **Upload your code**:
   ```bash
   scp -r . user@your-server:/home/user/behold-whatsapp/
   ```

4. **Install Python dependencies**:
   ```bash
   cd /home/user/behold-whatsapp/
   pip3 install -r requirements-whatsapp.txt
   ```

5. **Get SSL certificate**:
   ```bash
   sudo certbot certonly --nginx -d your-domain.com
   ```

6. **Configure nginx** (create `/etc/nginx/sites-available/whatsapp`):
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

7. **Enable site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/whatsapp /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

8. **Create systemd service** (`/etc/systemd/system/whatsapp-bot.service`):
   ```ini
   [Unit]
   Description=WhatsApp Bot
   After=network.target
   
   [Service]
   Type=simple
   User=user
   WorkingDirectory=/home/user/behold-whatsapp
   ExecStart=/usr/bin/python3 whatsapp_server.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

9. **Start service**:
   ```bash
   sudo systemctl enable whatsapp-bot
   sudo systemctl start whatsapp-bot
   ```

### Option 2: Docker Deployment

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements-whatsapp.txt .
   RUN pip install -r requirements-whatsapp.txt
   
   COPY . .
   
   EXPOSE 8000
   CMD ["python", "whatsapp_server.py"]
   ```

2. **Build and run**:
   ```bash
   docker build -t behold-whatsapp .
   docker run -d -p 8000:8000 --env-file .env behold-whatsapp
   ```

### Option 3: Cloud Platform Deployment

#### Railway
1. Connect your GitHub repository
2. Add environment variables
3. Deploy automatically

#### Heroku
1. Create Heroku app
2. Add environment variables
3. Deploy via Git

#### AWS/Google Cloud
1. Use App Engine or Elastic Beanstalk
2. Configure environment variables
3. Deploy with their CLI tools

## 📋 Step 7: Update Meta Configuration

### 7.1 Update Webhook URL

1. Go back to WhatsApp > Configuration
2. Update Callback URL to your production domain:
   - `https://your-domain.com/webhook`

### 7.2 Add Business Phone Number

1. Go to WhatsApp > Phone Numbers
2. Add your business phone number
3. Verify via SMS or call

### 7.3 Submit App for Review (Optional)

For production use with unlimited users:
1. Complete Business Verification
2. Submit app for review with use case
3. Wait for approval (can take 1-2 weeks)

## 🔧 Configuration Options

### Session Storage Options

**File Storage (Default)**:
```bash
SESSION_STORAGE_PATH=data/sessions
```

**PostgreSQL** (for high scale):
```bash
DATABASE_URL=postgresql://user:pass@host/db
```

**Redis Caching**:
```bash
REDIS_URL=redis://localhost:6379/0
```

### Rate Limiting

```bash
RATE_LIMIT_PER_MINUTE=30
```

### Logging Levels

```bash
LOG_LEVEL=INFO  # or DEBUG for detailed logs
```

## 🛠 Troubleshooting

### Common Issues

**1. Webhook Verification Failed**
- Check `WHATSAPP_VERIFY_TOKEN` matches exactly
- Ensure your server is running and accessible
- Check ngrok/server logs

**2. Messages Not Received**
- Verify webhook subscription is active
- Check phone number is added to allow list
- Ensure access token is valid

**3. Agent Not Responding**
- Check agent configuration in `behold_agent/`
- Verify Shopify credentials are correct
- Check server logs for errors

**4. Import Errors**
- Ensure all dependencies are installed
- Check Python path configuration
- Verify file structure matches documentation

### Debug Commands

**Check webhook status**:
```bash
curl https://your-domain.com/health
```

**View logs**:
```bash
tail -f /var/log/whatsapp-bot.log
```

**Test message sending**:
```bash
curl -X POST https://your-domain.com/send-message \
  -H "Content-Type: application/json" \
  -d '{"to": "1234567890", "message": "Test message"}'
```

### Getting Help

1. **Check logs** first for error details
2. **Meta Developer Docs**: [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
3. **Community**: WhatsApp Business API Developer Community
4. **GitHub Issues**: Report bugs or ask questions

## 🎯 Next Steps

### Recommended Enhancements

1. **Analytics**: Add message analytics and user metrics
2. **A/B Testing**: Test different message formats
3. **Multi-language**: Support multiple languages
4. **Rich Media**: Add support for images and videos
5. **AI Features**: Enhance with more AI capabilities

### Scaling Considerations

- **Database**: Move to PostgreSQL for user sessions
- **Caching**: Add Redis for performance
- **Load Balancing**: Use multiple server instances
- **Monitoring**: Add health checks and alerts

## 📊 Monitoring and Maintenance

### Key Metrics to Monitor

- Message volume and response times
- User engagement rates
- Error rates and types
- Server resource usage

### Regular Maintenance

- Monitor access token expiration
- Update dependencies regularly
- Back up user session data
- Review and optimize conversation flows

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit secrets to code
2. **HTTPS**: Always use HTTPS for webhooks
3. **Token Rotation**: Regularly rotate access tokens
4. **Rate Limiting**: Implement rate limiting
5. **Input Validation**: Validate all user inputs
6. **Monitoring**: Monitor for suspicious activity

---

## 🎉 You're Ready!

Your WhatsApp integration is now live! Users can:

- 💬 Chat naturally with your Shopify agent
- 🛍️ Browse and search products
- 🛒 Manage their shopping cart
- 💳 Get secure checkout links
- 🚚 Check shipping costs
- ℹ️ Get store information and policies

The agent provides a complete e-commerce experience through WhatsApp, making it easy for customers to shop directly through messaging!

