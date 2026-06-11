"""
Xovis SDK - CrewAI Adapter

Bridges the Universal Tool Adapter with modern multi-agent frameworks,
enabling SDK methods to be utilized as atomic tools within CrewAI
agents and AutoGPT task execution loops.
"""

from typing import Any

from xovis.skills.toolkit import XovisAIToolkit

try:
    from crewai.tools import BaseTool

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False


class XovisCrewAITool(BaseTool):
    """
    Asynchronous CrewAI Tool wrapper for Xovis SDK primitives.
    """

    func: Any

    def _run(self, **kwargs: Any) -> Any:
        """
        Disabled synchronous execution shim.

        Raises:
            NotImplementedError: High-throughput SDK operations strictly require async execution.
        """
        raise NotImplementedError("Xovis SDK tools strictly require asynchronous execution. Use _arun.")

    async def _arun(self, **kwargs: Any) -> Any:
        """
        Asynchronous execution path for CrewAI.
        """
        return await self.func(**kwargs)


def get_crewai_tools(toolkit: XovisAIToolkit) -> list[Any]:
    """
    Converts SDK primitives into CrewAI-native BaseTool objects.

    Args:
        toolkit (XovisAIToolkit): The initialized Xovis AI toolkit.

    Returns:
        List[BaseTool]: A list of executable CrewAI tools.

    Raises:
        ImportError: If the 'crewai' package is not installed.
    """
    if not CREWAI_AVAILABLE:
        raise ImportError("The 'crewai' package is required to use the CrewAI adapter. Install it via `pip install crewai`.")

    crewai_tools = []
    callable_primitives = toolkit.get_callable_tools()

    for primitive in callable_primitives:
        tool = XovisCrewAITool(name=primitive["name"], description=primitive["description"], func=primitive["callable"])
        crewai_tools.append(tool)

    return crewai_tools
