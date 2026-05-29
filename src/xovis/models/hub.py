from pydantic import BaseModel

class HubDevice(BaseModel):
    id: str
    name: str
