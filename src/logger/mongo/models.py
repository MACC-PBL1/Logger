from pydantic import BaseModel
from typing import Optional

class LogSource(BaseModel):
    filename: str
    lineno: int
    funcName: str
    pathname: str
    logger: str

class LogEntry(BaseModel):
    log_type: str
    subtype: str
    level: str
    message: str
    timestamp: str
    source: LogSource