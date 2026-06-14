import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath("src"))

from xovis.mcp.server import handle_list_tools

async def test():
    tools = await handle_list_tools()
    t = tools[0]
    print(t.name)
    print(t.description)
    print(json.dumps(t.inputSchema, indent=2))

asyncio.run(test())
