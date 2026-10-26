import os
import configparser
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama

from assistant.state import AgentState
from assistant.prompts import SYSTEM_PROMPT
from assistant.tools import query_shipments, get_route_stats, predict_delay
from assistant.guardrails import check_guardrails
from assistant.logger import log_interaction

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "settings.config"))

MAX_CALLS = int(config.get("guardrails", "max_tool_calls_per_session", fallback="4"))

# Bind tools to LLM
tools = [query_shipments, get_route_stats, predict_delay]
tool_map = {t.name: t for t in tools}

llm = ChatOllama(
    model=config.get("llm", "model_name", fallback="llama3"),
    temperature=float(config.get("llm", "temperature", fallback="0.0"))
).bind_tools(tools)
# --- NODES ---

def guardrail_node(state: AgentState):
    passed, reason = check_guardrails(state["user_prompt"], state.get("tool_call_count", 0), MAX_CALLS)
    if not passed:
        return {
            "messages": [AIMessage(content=reason)],
            "guardrail_refused": True
        }
    return {"guardrail_refused": False}

def agent_node(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_outputs = []
    tools_executed = []
    responses = []

    for call in last_message.tool_calls:
        tool_fn = tool_map[call["name"]]
        result = tool_fn.invoke(call["args"])
        tools_executed.append(call["name"])
        responses.append({"tool": call["name"], "args": call["args"], "result": result})
        tool_outputs.append(ToolMessage(tool_call_id=call["id"], content=str(result)))

    return {
        "messages": tool_outputs,
        "tools_called": tools_executed,
        "tool_responses": responses,
        "tool_call_count": state.get("tool_call_count", 0) + len(tools_executed)
    }

def logging_node(state: AgentState):
    final_output = state["messages"][-1].content
    log_interaction(
        prompt_sent=state["user_prompt"],
        tools_called=state.get("tools_called", []),
        tool_responses=state.get("tool_responses", []),
        final_output=str(final_output)
    )
    return {}

# --- ROUTING CONDITIONS ---

def route_after_guardrail(state: AgentState):
    if state.get("guardrail_refused", False):
        return "log"
    return "agent"

def route_after_agent(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        # Check budget before executing tools
        if state.get("tool_call_count", 0) >= MAX_CALLS:
            return "log"
        return "tools"
    return "log"

# --- WORKFLOW COMPILATION ---

workflow = StateGraph(AgentState)

workflow.add_node("guardrail", guardrail_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("log", logging_node)

workflow.set_entry_point("guardrail")

workflow.add_conditional_edges(
    "guardrail",
    route_after_guardrail,
    {"agent": "agent", "log": "log"}
)

workflow.add_conditional_edges(
    "agent",
    route_after_agent,
    {"tools": "tools", "log": "log"}
)

workflow.add_edge("tools", "agent")
workflow.add_edge("log", END)

assistant_app = workflow.compile()