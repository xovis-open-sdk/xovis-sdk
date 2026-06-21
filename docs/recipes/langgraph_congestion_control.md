# Recipe: LangGraph Congestion Control

This recipe demonstrates how to utilize the `xovis-sdk` within a cyclic LangGraph loop. 
The agent reads the local state via `XovisAgentMemory`, executes a task, and dynamically adjusts the hardware if network congestion is detected in the Data Plane.

```python
import asyncio
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from xovis import UnifiedDeviceClient
from xovis.skills.toolkit import XovisAIToolkit, XovisAgentMemory

class AgentState(TypedDict):
    messages: Annotated[list, "The message history."]
    hardware_state: str

async def process_hardware_loop():
    # Utilizing UnifiedDeviceClient for robust hybrid local/remote routing
    async with UnifiedDeviceClient(mac_address="00:26:8c:12:34:56", host="10.0.0.50") as device:
        toolkit = XovisAIToolkit(device)
        
        # Retrieving LangChain tools dynamically via the unified adapter registry
        tools = toolkit.get_tools("langchain")
        llm = ChatOpenAI(model="gpt-5.5").bind_tools(tools)

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
