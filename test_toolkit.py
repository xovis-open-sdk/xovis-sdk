import os
import sys

# Ensure we can import the toolkit
sys.path.insert(0, os.path.abspath("src"))

from xovis.api.device.client import DeviceClient
from xovis.skills.toolkit import XovisAIToolkit

client = DeviceClient(host="127.0.0.1", username="admin", password="password")
toolkit = XovisAIToolkit(client)
tools = toolkit.get_callable_tools()

print("Tool names:", [t["name"] for t in tools[:5]])
t = tools[0]
schema = t["args_model"].model_json_schema()
print("Schema properties:", schema.get("properties"))
print("Tool description:", t.get("description"))
