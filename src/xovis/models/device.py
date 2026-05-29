from pydantic import BaseModel

class Zone(BaseModel):
    id: int
    name: str

class SystemInfo(BaseModel):
    serial_number: str
    firmware_version: str
