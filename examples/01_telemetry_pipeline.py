import asyncio
from xovis import XovisTCPServer

async def main():
    server = XovisTCPServer()
    print("Starting Xovis Telemetry Pipeline...")
    # Logic to run the server would go here
    
if __name__ == "__main__":
    asyncio.run(main())
