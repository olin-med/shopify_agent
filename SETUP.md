# Shopify Agent Setup Instructions

## Environment Configuration

Create a `.env` file in the root directory with the following variables:

```bash
# Your Shopify store name (without .myshopify.com)
# Example: if your store is "mystore.myshopify.com", set this to "mystore"
SHOPIFY_STORE=your-store-name

# Shopify API version (recommended: 2025-07)
SHOPIFY_API_VERSION=2025-07

# Shopify Admin API Access Token
SHOPIFY_ADMIN_TOKEN=your-admin-access-token

# Shopify Storefront API Access Token
SHOPIFY_STOREFRONT_TOKEN=your-storefront-access-token
```

## Getting Your Shopify API Tokens

### 1. Admin API Token
1. Go to your Shopify Admin dashboard
2. Navigate to **Apps** > **App and sales channel settings**
3. Click **Develop apps**
4. Click **Create an app**
5. Give your app a name (e.g., "Behold Agent")
6. Click **Configure Admin API scopes**
7. Select the following scopes:
   - `read_products`
   - `read_orders`
   - `read_customers`
   - `read_shop`
   - `read_policies`
8. Click **Save**
9. Click **Install app**
10. Copy the **Admin API access token**

### 2. Storefront API Token
1. In the same app you created above
2. Click **Configure Storefront API scopes**
3. Select the following scopes:
   - `unauthenticated_read_product_listings`
   - `unauthenticated_read_product_inventory`
   - `unauthenticated_read_product_tags`
   - `unauthenticated_write_checkouts`
   - `unauthenticated_write_customers`
   - `unauthenticated_read_customers`
4. Click **Save**
5. Copy the **Storefront access token**

## Required API Scopes

### Admin API Scopes
- `read_products` - Read product information
- `read_orders` - Read order information
- `read_customers` - Read customer information
- `read_shop` - Read shop information
- `read_policies` - Read store policies

### Storefront API Scopes
- `unauthenticated_read_product_listings` - Read products for customers
- `unauthenticated_read_product_inventory` - Check product availability
- `unauthenticated_read_product_tags` - Read product tags
- `unauthenticated_write_checkouts` - Create checkouts
- `unauthenticated_write_customers` - Create customer accounts
- `unauthenticated_read_customers` - Read customer information

## Testing Your Setup

Once you've configured your `.env` file, you can test the agent by running:

```bash
python main.py
```

The agent should now be able to:
- ✅ Search and display products
- ✅ Create and manage shopping carts
- ✅ Generate checkout links
- ✅ Calculate shipping estimates
- ✅ Retrieve store policies
- ✅ Provide product recommendations

## Troubleshooting

### Common Issues

1. **"Access token is required" error**
   - Make sure your `.env` file is in the correct location
   - Verify your access tokens are correct
   - Check that the tokens have the required scopes

2. **"Shop name is required" error**
   - Make sure `SHOPIFY_STORE` is set correctly
   - Don't include `.myshopify.com` in the store name

3. **GraphQL validation errors**
   - The agent will automatically validate queries
   - If validation fails, it will retry without validation
   - Check your API version is supported

4. **Storefront API errors**
   - Ensure you have a Storefront access token
   - Verify the Storefront API scopes are configured
   - Check that your products are published and available

### Getting Help

If you encounter issues:
1. Check the error messages in the agent responses
2. Verify your API tokens have the correct scopes
3. Test with a simple product search first
4. Check your Shopify store's API limits

## Security Notes

- Never commit your `.env` file to version control
- Keep your API tokens secure
- Regularly rotate your access tokens
- Use the minimum required scopes for your use case



