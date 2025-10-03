# Railway Deployment Guide - Behold Agent Only

This guide deploys just the Python FastAPI agent to Railway. You'll need to run the WhatsApp bridge separately.

## Architecture

- **This deployment**: Python FastAPI Agent (port 8000) - Processes messages through the Behold Shopify agent
- **Separate deployment needed**: Node.js WhatsApp Bridge (port 3001) - Handles WhatsApp Web.js connection

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. A GitHub repository with your code
3. Your Shopify store credentials
4. A separate WhatsApp bridge deployment (or run locally)

## Required Environment Variables

Set these environment variables in your Railway project:

### Shopify Configuration
```
SHOPIFY_STORE=your-store-name
SHOPIFY_API_VERSION=2025-07
SHOPIFY_ADMIN_TOKEN=your-admin-access-token
SHOPIFY_STOREFRONT_TOKEN=your-storefront-access-token
```

### WhatsApp Bridge Configuration
```
WHATSAPP_BRIDGE_URL=https://your-whatsapp-bridge.railway.app
```

### Optional Configuration
```
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

## Deployment Steps

### 1. Deploy the Agent

1. **Connect GitHub Repository:**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - **Important**: Set the root directory to `behold_agent/`

2. **Configure Environment Variables:**
   - Add all the required environment variables listed above
   - Set `WHATSAPP_BRIDGE_URL` to your WhatsApp bridge URL

3. **Deploy:**
   - Railway will automatically detect the Dockerfile
   - The deployment will start automatically

### 2. Deploy the WhatsApp Bridge (Separate)

You'll need to deploy the WhatsApp bridge separately. You can:

1. **Deploy to Railway** (recommended):
   - Create another Railway project
   - Set root directory to `whatsapp-bridge/`
   - Deploy the Node.js bridge

2. **Run locally**:
   - Run `cd whatsapp-bridge && npm start`
   - Use ngrok or similar to expose it publicly
   - Set `WHATSAPP_BRIDGE_URL` to your ngrok URL

### 3. Test the Integration

1. **Check Agent Health:**
   - Visit `https://your-agent.railway.app/health`

2. **Check Bridge Health:**
   - Visit `https://your-bridge.railway.app/health`

3. **Test WhatsApp:**
   - Visit `https://your-bridge.railway.app/qr` to scan QR code
   - Send a message to the WhatsApp number

## File Structure

```
behold_agent/
├── Dockerfile                 # Docker configuration
├── requirements.txt          # Python dependencies
├── railway.json             # Railway configuration
├── .dockerignore            # Docker ignore file
├── DEPLOYMENT.md            # This guide
├── main.py                  # FastAPI application
├── pyproject.toml           # Project configuration
└── agent/                   # Agent implementation
    ├── agent.py             # Main Behold agent
    ├── prompt.py            # Agent prompts
    └── tools/               # Agent tools
        ├── shopify_tool.py  # Shopify integration
        └── whatsapp/        # WhatsApp tools
            └── whatsapp_tool.py # WhatsApp bridge integration
```

## Health Check

The application provides a health check endpoint at `/health` that returns:
```json
{
  "status": "healthy",
  "service": "Behold WhatsApp Shopify Agent"
}
```

## Communication Flow

1. User sends WhatsApp message
2. WhatsApp Bridge receives message
3. Bridge sends to Agent: `POST /process-whatsapp-message`
4. Agent processes with Behold Shopify agent
5. Agent returns response to Bridge
6. Bridge sends response via WhatsApp

## Troubleshooting

### Common Issues

1. **Bridge Connection Error:**
   - Check `WHATSAPP_BRIDGE_URL` is correct
   - Ensure bridge is running and accessible
   - Check bridge health endpoint

2. **Shopify API Errors:**
   - Verify Shopify tokens have correct permissions
   - Check store name is correct (without .myshopify.com)

3. **Agent Not Responding:**
   - Check agent logs in Railway
   - Verify all environment variables are set
   - Test health endpoint

## Next Steps

1. Deploy both services
2. Test the integration
3. Monitor logs for any issues
4. Consider adding persistent storage for conversations
