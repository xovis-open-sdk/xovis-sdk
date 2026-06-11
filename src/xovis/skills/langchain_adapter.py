"""
Xovis SDK - LangChain Integration Adapter

Transforms the Universal Tool Adapter into native LangChain StructuredTools,
enabling direct integration into LangGraph cyclic reasoning loops and
standard AgentExecutors.
"""

from typing import Any

from xovis.skills.toolkit import XovisAIToolkit

try:
    from langchain_core.tools import StructuredTool

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


def get_langchain_tools(toolkit: XovisAIToolkit) -> list[Any]:
    """
    Converts SDK primitives into LangChain-native tool objects.

    Args:
        toolkit (XovisAIToolkit): The initialized Xovis AI toolkit.

    Returns:
        List[StructuredTool]: A list of executable LangChain tools.

    Raises:
        ImportError: If the langchain-core package is not installed.
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("The 'langchain-core' package is required to use the LangChain adapter. Install it via `pip install langchain-core`.")

    langchain_tools = []

    # We use execute_tool as the entry point for all tools to ensure
    # that the toolkit's internal routing and safety logic is preserved.
    callable_primitives = toolkit.get_callable_tools()

    for primitive in callable_primitives:
        name = primitive["name"]

        # We create a closure that calls toolkit.execute_tool
        async def tool_func(tool_name=name, **kwargs):
            res_json = await toolkit.execute_tool(tool_name, kwargs)
            import json

            return json.loads(res_json)

        tool = StructuredTool.from_function(
            coroutine=tool_func,
            name=name,
            description=primitive["description"],
            args_schema=primitive["args_model"],
        )
        langchain_tools.append(tool)

    return langchain_tools
