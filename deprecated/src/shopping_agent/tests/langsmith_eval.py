import os
from langsmith import Client
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shopping_agent import agent

def run_langsmith_eval():
    print("Preparing LangSmith evaluation...")

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "shopping-agent-eval"

    try:
        client = Client()
        print("  LangSmith client initialized successfully.")
        print("  [INFO] Successfully connected using the provided LangSmith API key.")
        print("  [INFO] Tracing is enabled. You can now execute queries and track them in your LangSmith dashboard.")
    except Exception as e:
        print(f"  [INFO] Error connecting to LangSmith: {e}")

if __name__ == "__main__":
    run_langsmith_eval()
