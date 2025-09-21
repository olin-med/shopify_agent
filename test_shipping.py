#!/usr/bin/env python3
"""
Test script to verify shipping calculation functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from behold_agent.agent.tools.shopify_tool import (
    search_products,
    create_cart,
    calculate_shipping_estimate
)

def test_shipping_calculation():
    """Test the full shipping calculation workflow"""

    print("🧪 Testing Shopify Shipping Calculation...")
    print("=" * 50)

    # Step 1: Search for products
    print("\n1️⃣ Searching for products...")
    product_result = search_products("shirt", 5)

    if product_result.get("status") != "success":
        print(f"❌ Product search failed: {product_result.get('error_message')}")
        return False

    products = product_result.get("data", {}).get("products", [])
    if not products:
        print("❌ No products found")
        return False

    print(f"✅ Found {len(products)} products")

    # Get first product variant for cart
    first_product = products[0]
    variants = first_product.get("variants", {}).get("edges", [])

    if not variants:
        print("❌ No variants found for first product")
        return False

    variant_id = variants[0]["node"]["id"]
    product_title = first_product.get("title", "Unknown Product")

    print(f"📦 Using product: {product_title}")
    print(f"🆔 Variant ID: {variant_id}")

    # Step 2: Create cart with product
    print("\n2️⃣ Creating cart...")
    cart_lines = [{"merchandiseId": variant_id, "quantity": 1}]
    cart_result = create_cart(cart_lines)

    if cart_result.get("status") != "success":
        print(f"❌ Cart creation failed: {cart_result.get('error_message')}")
        return False

    cart_data = cart_result.get("data", {})
    cart_id = cart_data.get("cart_id")

    if not cart_id:
        print("❌ No cart ID returned")
        return False

    print(f"✅ Cart created: {cart_id}")

    # Step 3: Calculate shipping
    print("\n3️⃣ Calculating shipping rates...")

    # Test addresses
    test_addresses = [
        {
            "name": "US Address",
            "address": {
                "country": "US",
                "province": "CA",
                "city": "Los Angeles",
                "zip": "90210"
            }
        },
        {
            "name": "Canada Address",
            "address": {
                "country": "CA",
                "province": "ON",
                "city": "Toronto",
                "zip": "M5V 3A8"
            }
        },
        {
            "name": "UK Address",
            "address": {
                "country": "GB",
                "city": "London",
                "zip": "SW1A 1AA"
            }
        }
    ]

    shipping_results = []

    for test_case in test_addresses:
        print(f"\n📍 Testing {test_case['name']}...")

        shipping_result = calculate_shipping_estimate(cart_id, test_case["address"])

        if shipping_result.get("status") == "success":
            shipping_data = shipping_result.get("data", {})
            options = shipping_data.get("shipping_options", [])

            print(f"✅ {len(options)} shipping options found")

            for i, option in enumerate(options[:3], 1):  # Show first 3
                title = option.get("title", "Unknown")
                cost = option.get("estimatedCost", {})
                amount = cost.get("amount", "N/A")
                currency = cost.get("currencyCode", "")

                print(f"   {i}. {title}: {amount} {currency}")

            shipping_results.append({
                "location": test_case["name"],
                "success": True,
                "options_count": len(options)
            })

        else:
            error_msg = shipping_result.get("error_message", "Unknown error")
            print(f"❌ Shipping calculation failed: {error_msg}")

            shipping_results.append({
                "location": test_case["name"],
                "success": False,
                "error": error_msg
            })

    # Summary
    print("\n" + "=" * 50)
    print("📊 SHIPPING TEST SUMMARY")
    print("=" * 50)

    successful_tests = sum(1 for r in shipping_results if r["success"])
    total_tests = len(shipping_results)

    print(f"✅ Successful tests: {successful_tests}/{total_tests}")

    for result in shipping_results:
        status = "✅" if result["success"] else "❌"
        location = result["location"]

        if result["success"]:
            options = result["options_count"]
            print(f"{status} {location}: {options} shipping options")
        else:
            error = result["error"]
            print(f"{status} {location}: {error}")

    if successful_tests > 0:
        print(f"\n🎉 Shipping calculation is working! Agent can calculate shipping fees.")
        return True
    else:
        print(f"\n⚠️  Shipping calculation needs setup. Check store configuration.")
        return False

if __name__ == "__main__":
    test_shipping_calculation()