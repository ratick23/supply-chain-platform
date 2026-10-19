import sys
from langchain_core.messages import HumanMessage
from assistant.graph import assistant_app

def start_cli():
    print("=" * 65)
    print(" Supply Chain Intelligence GenAI Assistant (LangGraph CLI)")
    print(" Type 'exit' or 'quit' to quit.")
    print("=" * 65)

    while True:
        try:
            user_input = input("\nUser > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Exiting assistant session. Goodbye.")
                sys.exit(0)

            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "user_prompt": user_input,
                "tools_called": [],
                "tool_responses": [],
                "tool_call_count": 0,
                "guardrail_refused": False
            }

            result = assistant_app.invoke(initial_state)
            assistant_response = result["messages"][-1].content
            print(f"\nAssistant > {assistant_response}")

        except KeyboardInterrupt:
            print("\nSession interrupted.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    start_cli()