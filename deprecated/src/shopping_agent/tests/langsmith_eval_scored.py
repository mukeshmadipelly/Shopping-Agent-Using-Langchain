import os
import json
from typing import List, Dict
from langsmith import Client
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shopping_agent import agent

# LangSmith configuration
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "shopping-agent-eval"

client = Client()

def run_agent_query(query: str, history: List[Dict] | None = None) -> Dict:
    """Run the agent and return the trace ID and result.
    Optional history is prepended so multi-turn references (e.g. 'the first one') resolve.
    """
    messages = (history or []) + [{"role": "user", "content": query}]
    result = agent.invoke({"messages": messages})
    return {
        "query": query,
        "response": result["messages"][-1].text,
        "tool_calls": [
            {
                "name": tc["name"],
                "args": tc["args"]
            }
            for msg in result["messages"]
            if hasattr(msg, "tool_calls") and msg.tool_calls
            for tc in msg.tool_calls
        ]
    }

def llm_as_judge(query: str, response: str, expected_behavior: str) -> Dict:
    """Score the response using an LLM judge."""
    judge_prompt = f"""
You are an evaluation judge for a shopping assistant.

Query: "{query}"
Expected behavior: {expected_behavior}
Actual response: "{response}"

Answer **PASS** if the response satisfies all expectations, otherwise answer **FAIL**.
Return only the word PASS or FAIL (no extra text).
"""
    try:
        judge = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")
        judge_response = judge.invoke([HumanMessage(content=judge_prompt)])
        # Extract text from response (handles list or string content)
        response_text = judge_response.content[0]['text'] if isinstance(judge_response.content, list) else judge_response.content
        return {
            "score": 1 if "PASS" in response_text.upper() or "CORRECT" in response_text.upper() else 0,
            "reasoning": response_text
        }
    except Exception as e:
        return {"score": 0, "reasoning": f"Judge failed: {e}", "error": str(e)}

# Test cases: query + expected behavior + expected tool calls
TEST_CASES = [
    {"query": "write me a poem about the weather", "expected": "Guardrail: refuse non-shopping request politely", "expected_tool_calls": []},
    {"query": "I want to buy organic honey with 4.5+ rating and less than $20 price", "expected": "Search products with is_organic=True, max_price=20, filter by rating", "expected_tool_calls": ["search_products", "get_product_reviews"]},
    {"query": "the first one", "expected": "Checkout the product referenced in previous message (ID:1)", "expected_tool_calls": ["checkout"]},
    {"query": "what have I ordered before?", "expected": "Return order history from database via get_order_history", "expected_tool_calls": ["get_order_history"]},
    {"query": "organic almonds under $15", "expected": "Search with is_organic=True, max_price=15 filter", "expected_tool_calls": ["search_products", "get_product_reviews"]},
]

def run_scored_evaluation():
    print("Running Scored LangSmith Evaluation...")
    print("  Note: Your API key is tracing-only (lsv2_pt_...), so datasets can't be created.")
    print("  Running queries locally and scoring with an LLM-as-judge.\n")

    results = []

    # Shared conversation history (simulates Streamlit session state across turns)
    history: List[Dict] = []

    for i, example in enumerate(TEST_CASES, start=1):
        print(f"  Test {i}/5: '{example['query'][:50]}'")
        # Pass accumulated conversation to agent (simulates real session)
        agent_result = run_agent_query(example['query'], history)
        history.append({"role": "user", "content": example['query']})
        history.append({"role": "assistant", "content": agent_result['response']})
        judge_result = llm_as_judge(example['query'], agent_result['response'], example['expected'])

        actual_tools = [tc['name'] for tc in agent_result['tool_calls']]
        # Tool check: all expected tools must be called (ignore extra duplicate calls)
        tool_ok = all(t in actual_tools for t in example['expected_tool_calls'])

        result_record = {
            "query": example['query'],
            "response": agent_result['response'],
            "tool_calls": agent_result['tool_calls'],
            "judge_score": judge_result['score'],
            "judge_reasoning": judge_result['reasoning'],
            "tool_ok": tool_ok,
            "passed": judge_result['score'] == 1 and tool_ok
        }
        results.append(result_record)
        print(f"      Tools: {actual_tools} | Judge: {'PASS' if judge_result['score']==1 else 'FAIL'} | Tool-check: {'PASS' if tool_ok else 'FAIL'}")
        print(f"      → {'PASS' if result_record['passed'] else 'FAIL'}")
        print(f"      Response: {agent_result['response'][:100]}...\n")

    print("=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    passed = sum(r['passed'] for r in results)
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {len(results)-passed}")
    print(f"  Pass rate: {passed/len(results)*100:.1f}%")
    print("\n  Each query also appears as a trace in your LangSmith project 'shopping-agent-eval'.")
    print("  Open https://smith.langchain.com to see the full traces with tool calls.")

if __name__ == "__main__":
    run_scored_evaluation()
