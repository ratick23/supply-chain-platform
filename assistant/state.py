from typing import Annotated, Sequence, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_prompt: str
    tools_called: Annotated[List[str], operator.add]
    tool_responses: Annotated[List[Dict[str, Any]], operator.add]
    tool_call_count: int
    guardrail_refused: bool