from typing import Annotated
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableLambda
from src.utils.utils import handle_tool_error


@tool
def python_repl_environment(code: Annotated[str, 'Code provided for execution and result generation']):
    pass







def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)],
        exception_key="error"
    )