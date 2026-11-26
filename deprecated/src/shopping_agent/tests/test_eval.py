import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shopping_agent import agent

def test_tool_call_accuracy():
    print("Running Tool Call Accuracy Eval...")

    # Test query 1: Organic honey under $20
    query = "organic honey under $20"
    result = agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Check messages for tool calls
    messages = result["messages"]
    tool_calls_found = False
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "search_products":
                    tool_calls_found = True
                    args = tc["args"]
                    print(f"  Query: '{query}' -> Tool: search_products, Args: {args}")
                    assert args.get("is_organic") is True, f"Expected is_organic=True, got {args.get('is_organic')}"
                    assert args.get("max_price") == 20 or args.get("max_price") == 20.0, f"Expected max_price=20, got {args.get('max_price')}"

    assert tool_calls_found, "Expected search_products tool call was not found."
    print("  [PASS] Tool call accuracy test passed!")

if __name__ == "__main__":
    test_tool_call_accuracy()
