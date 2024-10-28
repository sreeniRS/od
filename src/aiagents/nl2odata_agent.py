from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda, Runnable
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langgraph.graph import END, StateGraph, START
from src.utils.utils import handle_tool_error

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class OutputState(TypedDict):
    odata_query: str

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State):
        while True:
            result = self.runnable.invoke(state)
            
            
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break

        return {"messages": result}

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)],
        exception_key="error"
    )

def create_graph(assistant_runnable, tools):
    builder = StateGraph(State)
    builder.add_node("Text2Odata", Assistant(assistant_runnable))
    builder.add_node("tools", create_tool_node_with_fallback(tools))
    
    builder.add_edge(START, "Text2Odata")
    builder.add_conditional_edges("Text2Odata", tools_condition)
    builder.add_edge("tools", "Text2Odata")

    return builder.compile()

