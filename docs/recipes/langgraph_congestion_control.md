# Recipe: LangGraph Congestion Control

This recipe demonstrates how to utilize the `xovis-sdk` within a cyclic LangGraph loop. 
The agent reads the local state via `XovisAgentMemory`, executes a task, and dynamically adjusts the hardware if network congestion is detected in the Data Plane.

```python
import asyncio
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from xovis.api.device.client import DeviceClient
from xovis.skills.toolkit import XovisAIToolkit, XovisAgentMemory
from xovis.skills.langchain_adapter import get_langchain_tools

class AgentState(TypedDict):
    messages: Annotated[list, "The message history."]
    hardware_state: str

async def process_hardware_loop():
    async with DeviceClient("10.0.0.50", "admin", "password") as device:
        toolkit = XovisAIToolkit(device)
        tools = get_langchain_tools(toolkit)
        llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)

        memory = XovisAgentMemory(device.cache._state)
        compressed_state = memory.get_compressed_state()

        # Initialize the LangGraph State
        def agent_node(state: AgentState):
            response = llm.invoke(state["messages"])
            return {"messages": [response]}

        # Define the routing logic (Tool execution vs END)
        # ... standard LangGraph ToolNode execution omitted for brevity ...
        
        # Execute the graph
        print("LangGraph Execution Initialized with physical hardware access.")
```
