#!/usr/bin/env python3
"""
Simple test script to verify shipping calculation functionality
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import only the necessary modules without the agent
try:
    from behold_agent.agent.tools.shopify_tool import (
        search_products,
        create_cart,
        calculate_shipping_estimate
    )

    def test_shipping_api():
        """Test shipping calculation functionality"""
        print("🧪 Testing Shopify Shipping API Integration...")
        print("=" * 60)

        # Test 1: Check environment setup
        print("\n1️⃣ Checking environment setup...")

        from dotenv import load_dotenv
        load_dotenv()

        required_env_vars = [
            "SHOPIFY_STORE",
            "SHOPIFY_STOREFRONT_TOKEN",
            "SHOPIFY_API_VERSION"
        ]

        env_check = True
        for var in required_env_vars:
            value = os.getenv(var)
            if not value or value.startswith("your-"):
                print(f"❌ {var} not configured")
                env_check = False
            else:
                print(f"✅ {var} configured")

        if not env_check:
            print("\n⚠️  Please configure your .env file with actual Shopify credentials")
            print("🔧 Update the values in .env file and try again")
            return False

        # Test 2: Search for products (minimal test)
        print("\n2️⃣ Testing product search...")
        try:
            result = search_products("", 1)  # Empty query to get any products

            if result.get("status") == "success":
                products = result.get("data", {}).get("products", [])
                if products:
                    print(f"✅ Found {len(products)} product(s)")
                    product = products[0]
                    print(f"📦 Sample product: {product.get('title', 'Unknown')}")

                    # Check if product has variants for cart creation
                    variants = product.get("variants", {}).get("edges", [])
                    if variants:
                        variant_id = variants[0]["node"]["id"]
                        print(f"🆔 Sample variant ID: {variant_id}")
                        return variant_id
                    else:
                        print("❌ No variants found in products")
                        return False
                else:
                    print("❌ No products found in store")
                    return False
            else:
                error = result.get("error_message", "Unknown error")
                print(f"❌ Product search failed: {error}")
                return False

        except Exception as e:
            print(f"❌ Product search error: {str(e)}")
            return False

    def test_cart_and_shipping(variant_id):
        """Test cart creation and shipping calculation"""
        print("\n3️⃣ Testing cart creation...")

        try:
            # Create cart with one item
            cart_lines = [{"merchandiseId": variant_id, "quantity": 1}]
            cart_result = create_cart(cart_lines)

            if cart_result.get("status") == "success":
                cart_data = cart_result.get("data", {})
                cart_id = cart_data.get("cart_id")

                if cart_id:
                    print(f"✅ Cart created: {cart_id}")

                    # Test shipping calculation
                    print("\n4️⃣ Testing shipping calculation...")

                    test_address = {
                        "country": "US",
                        "province": "CA",
                        "city": "Los Angeles",
                        "zip": "90210"
                    }

                    shipping_result = calculate_shipping_estimate(cart_id, test_address)

                    if shipping_result.get("status") == "success":
                        shipping_data = shipping_result.get("data", {})
                        options = shipping_data.get("shipping_options", [])

                        print(f"✅ Shipping calculation successful!")
                        print(f"📦 Found {len(options)} shipping option(s)")

                        if options:
                            for i, option in enumerate(options[:3], 1):
                                title = option.get("title", "Standard Shipping")
                                cost = option.get("estimatedCost", {})
                                amount = cost.get("amount", "0.00")
                                currency = cost.get("currencyCode", "USD")

                                print(f"   {i}. {title}: ${amount} {currency}")
                        else:
                            print("⚠️  No shipping options returned (may need store shipping setup)")

                        return True
                    else:
                        error = shipping_result.get("error_message", "Unknown error")
                        print(f"❌ Shipping calculation failed: {error}")
                        return False
                else:
                    print("❌ No cart ID returned")
                    return False
            else:
                error = cart_result.get("error_message", "Unknown error")
                print(f"❌ Cart creation failed: {error}")
                return False

        except Exception as e:
            print(f"❌ Cart/shipping test error: {str(e)}")
            return False

    def main():
        """Run all tests"""
        variant_id = test_shipping_api()

        if variant_id:
            success = test_cart_and_shipping(variant_id)

            print("\n" + "=" * 60)
            print("📊 FINAL RESULTS")
            print("=" * 60)

            if success:
                print("🎉 SUCCESS: Shipping calculation is working!")
                print("✅ Your agent can calculate shipping fees for users")
                print("\nℹ️  Agent Usage:")
                print("   • Users can ask: 'How much is shipping?'")
                print("   • Agent will: calculate_shipping_estimate(cart_id, address)")
                print("   • Returns: shipping options with costs")
            else:
                print("⚠️  PARTIAL: Basic API works, shipping needs store configuration")
                print("🔧 Next steps:")
                print("   • Check Shopify Admin → Settings → Shipping and delivery")
                print("   • Configure shipping zones and rates")
                print("   • Test with real store data")
        else:
            print("\n❌ FAILED: Basic API connection issues")
            print("🔧 Check your .env configuration and Shopify credentials")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("🔧 Make sure you're in the shopify_agent directory")
    print("📁 Current directory:", os.getcwd())