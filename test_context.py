#!/usr/bin/env python3
"""
Test script for context window functionality.
Tests 5-turn context management and state persistence.
"""

import sys
import os

# Add the behold_agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'behold_agent'))

from agent.session_context import SessionContext, ContextManager

def test_basic_context():
    """Test basic context creation and turn management."""
    print("=" * 60)
    print("TEST 1: Basic Context Creation")
    print("=" * 60)

    context = SessionContext(user_id="test_user", session_id="test_session")

    # Add 3 turns
    context.add_turn("Show me shoes", "Here are some great shoes from our collection!")
    context.add_turn("Add the red ones to cart", "Added red sneakers to your cart! 🛒")
    context.add_turn("What's the total?", "Your cart total is $89.99")

    print(f"✅ Created context with {len(context.conversation_history)} messages")
    print(f"✅ Expected: 6 messages (3 turns × 2)")

    # Check history
    assert len(context.conversation_history) == 6, "Should have 6 messages (3 turns)"
    print("\n📝 Conversation History:")
    for i, entry in enumerate(context.conversation_history):
        print(f"   {i+1}. [{entry.role}]: {entry.message[:50]}...")

    print("\n✅ TEST 1 PASSED\n")


def test_context_window_limit():
    """Test 5-turn window enforcement."""
    print("=" * 60)
    print("TEST 2: 5-Turn Window Limit")
    print("=" * 60)

    context = SessionContext(user_id="test_user", session_id="test_session", max_turns=5)

    # Add 7 turns (should keep only last 5)
    turns = [
        ("Turn 1 user", "Turn 1 assistant"),
        ("Turn 2 user", "Turn 2 assistant"),
        ("Turn 3 user", "Turn 3 assistant"),
        ("Turn 4 user", "Turn 4 assistant"),
        ("Turn 5 user", "Turn 5 assistant"),
        ("Turn 6 user", "Turn 6 assistant"),
        ("Turn 7 user", "Turn 7 assistant"),
    ]

    for user_msg, asst_msg in turns:
        context.add_turn(user_msg, asst_msg)

    print(f"✅ Added 7 turns")
    print(f"✅ Context now has {len(context.conversation_history)} messages")
    print(f"✅ Expected: 10 messages (5 turns × 2)")

    # Should only have last 5 turns (10 messages)
    assert len(context.conversation_history) == 10, "Should have exactly 10 messages (5 turns)"

    # First message should be Turn 3
    first_msg = context.conversation_history[0].message
    assert "Turn 3" in first_msg, f"Expected Turn 3, got: {first_msg}"

    print(f"\n📝 Oldest message in window: {first_msg}")
    print(f"📝 Newest message in window: {context.conversation_history[-1].message}")

    print("\n✅ TEST 2 PASSED\n")


def test_shopping_state():
    """Test shopping state tracking."""
    print("=" * 60)
    print("TEST 3: Shopping State Tracking")
    print("=" * 60)

    context = SessionContext(user_id="test_user", session_id="test_session")

    # Track product searches
    context.add_product_search("shoes", [
        {"id": "1", "title": "Red Sneakers", "price": "89.99"},
        {"id": "2", "title": "Blue Sneakers", "price": "79.99"},
    ])

    context.add_product_search("shirts", [
        {"id": "3", "title": "White Shirt", "price": "39.99"},
    ])

    print(f"✅ Added 2 product searches")
    print(f"✅ Tracked searches: {[s['query'] for s in context.recent_product_searches]}")

    # Track cart
    context.update_cart("cart_123")
    print(f"✅ Cart ID: {context.current_cart_id}")

    # Track shipping
    context.update_shipping_address({
        "country": "US",
        "province": "CA",
        "city": "Los Angeles",
        "zip": "90210"
    })
    print(f"✅ Shipping: {context.shipping_address}")

    # Track preferences
    context.update_preferences({"size": "M", "color": "red"})
    print(f"✅ Preferences: {context.user_preferences}")

    print("\n✅ TEST 3 PASSED\n")


def test_context_summary():
    """Test context summary generation."""
    print("=" * 60)
    print("TEST 4: Context Summary Generation")
    print("=" * 60)

    context = SessionContext(user_id="test_user", session_id="test_session")

    # Add conversation
    context.add_turn("Show me red shoes", "Here are some red shoes!")
    context.add_turn("Add the first one", "Added to cart!")

    # Add shopping state
    context.add_product_search("red shoes", [
        {"id": "1", "title": "Red Sneakers", "price": "89.99"},
    ])
    context.update_cart("cart_abc123")
    context.update_shipping_address({"country": "US", "province": "CA", "city": "LA"})
    context.update_preferences({"size": "L"})

    summary = context.get_context_summary()

    print("📝 Context Summary:")
    print("-" * 60)
    print(summary)
    print("-" * 60)

    # Verify summary contains key info
    assert "Recent Conversation" in summary
    assert "Active Cart" in summary
    assert "Recent Searches" in summary
    assert "Shipping Address" in summary
    assert "Preferences" in summary

    print("\n✅ TEST 4 PASSED\n")


def test_context_manager():
    """Test ContextManager multi-user support."""
    print("=" * 60)
    print("TEST 5: Context Manager Multi-User")
    print("=" * 60)

    manager = ContextManager()

    # Create contexts for 2 users
    context1 = manager.get_or_create_context("user1", "session1")
    context2 = manager.get_or_create_context("user2", "session2")

    # Add different data
    context1.add_turn("User 1 message", "User 1 response")
    context2.add_turn("User 2 message", "User 2 response")

    # Verify isolation
    assert len(context1.conversation_history) == 2
    assert len(context2.conversation_history) == 2
    assert context1.conversation_history[0].message == "User 1 message"
    assert context2.conversation_history[0].message == "User 2 message"

    print(f"✅ User 1 context: {len(context1.conversation_history)} messages")
    print(f"✅ User 2 context: {len(context2.conversation_history)} messages")
    print(f"✅ Contexts are properly isolated")

    # Test retrieval
    retrieved = manager.get_context("user1", "session1")
    assert retrieved == context1
    print(f"✅ Context retrieval works")

    print("\n✅ TEST 5 PASSED\n")


def test_serialization():
    """Test context serialization."""
    print("=" * 60)
    print("TEST 6: Context Serialization")
    print("=" * 60)

    # Create and populate context
    context = SessionContext(user_id="test_user", session_id="test_session")
    context.add_turn("Hello", "Hi there!")
    context.update_cart("cart_123")
    context.add_product_search("shoes", [{"id": "1", "title": "Shoes"}])

    # Serialize
    data = context.to_dict()
    print(f"✅ Serialized context: {list(data.keys())}")

    # Deserialize
    restored = SessionContext.from_dict(data)

    # Verify
    assert restored.user_id == context.user_id
    assert restored.session_id == context.session_id
    assert len(restored.conversation_history) == len(context.conversation_history)
    assert restored.current_cart_id == context.current_cart_id

    print(f"✅ Restored context matches original")
    print(f"✅ User ID: {restored.user_id}")
    print(f"✅ Messages: {len(restored.conversation_history)}")
    print(f"✅ Cart: {restored.current_cart_id}")

    print("\n✅ TEST 6 PASSED\n")


def main():
    """Run all tests."""
    print("\n🧪 TESTING 5-TURN CONTEXT WINDOW\n")

    try:
        test_basic_context()
        test_context_window_limit()
        test_shopping_state()
        test_context_summary()
        test_context_manager()
        test_serialization()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📊 Test Summary:")
        print("   • Basic context creation: ✅")
        print("   • 5-turn window enforcement: ✅")
        print("   • Shopping state tracking: ✅")
        print("   • Context summary generation: ✅")
        print("   • Multi-user context manager: ✅")
        print("   • Serialization/deserialization: ✅")
        print("\n🎉 Context window implementation is working correctly!\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise


if __name__ == "__main__":
    main()
