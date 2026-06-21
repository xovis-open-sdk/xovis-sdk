# Recipe: CrewAI Fleet Monitoring

This recipe demonstrates how to utilize the `xovis-sdk` with CrewAI agents. 
The agent accesses the toolkit tools via the `crewai` adapter to interact with the device.

```python
import asyncio
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

from xovis import UnifiedDeviceClient
from xovis.skills.toolkit import XovisAIToolkit

async def run_crewai_monitoring():
    # Utilizing UnifiedDeviceClient for robust hybrid local/remote routing
    async with UnifiedDeviceClient(mac_address="00:26:8c:12:34:56", host="10.0.0.50") as device:
        toolkit = XovisAIToolkit(device)
        
        # Retrieving CrewAI tools dynamically via the unified adapter registry
        crewai_tools = toolkit.get_tools("crewai")
        llm = ChatOpenAI(model="gpt-5.5")

        # Define the monitoring agent
        monitor_agent = Agent(
            role="Xovis Sensor Monitor",
            goal="Analyze the device telemetry and ensure congestion control.",
            backstory="You are an AI assistant specialized in Xovis hardware.",
            verbose=True,
            tools=crewai_tools,
            llm=llm
        )

        # Define the task
        task = Task(
            description="Fetch the system info and recent historical counts. Check if any intervention is needed.",
            expected_output="A summary report of the device status.",
            agent=monitor_agent
        )

        # Define the crew
        crew = Crew(
            agents=[monitor_agent],
            tasks=[task],
            process=Process.sequential
        )

        # Execute
        result = crew.kickoff()
        print("Crew execution result:", result)
```
