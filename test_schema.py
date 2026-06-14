import asyncio
from xovis.skills.toolkit import XovisAIToolkit
from xovis.mcp.server import _normalize_schema

async def main():
    toolkit = XovisAIToolkit(host="127.0.0.1", user="admin", password="password")
    tools = toolkit.get_tools()
    print("Tool Name:", tools[0].name)
    print("Tool Description:", tools[0].description)
    schema = tools[0].args_schema.model_json_schema() if tools[0].args_schema else {}
    print("Schema Properties:", schema.get("properties"))
    
    # Try getting the normalized schema from server
    from mcp.server.models import InitializationOptions
    
    # Let's inspect all tools directly
    print("\nTotal tools:", len(tools))
    for t in tools[:3]:
        print(f"Name: {t.name}, Desc: {bool(t.description)}, Props have desc: {any('description' in v for v in t.args_schema.model_json_schema().get('properties', {}).values()) if t.args_schema else False}")

asyncio.run(main())
