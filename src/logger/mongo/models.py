from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, Union
from datetime import datetime

class LogSource(BaseModel):
    filename: Optional[str] = None
    lineno: Optional[int] = None
    funcName: Optional[str] = None
    pathname: Optional[str] = None
    logger: Optional[str] = None

class LogEntry(BaseModel):
    level: Optional[str] = None
    message: str
    timestamp: Union[datetime, str] = Field(default_factory=datetime.now)

    log_type: Optional[str] = None
    subtype: Optional[str] = None
    source: Optional[Union[LogSource, Dict[str, Any]]] = None

    service: Optional[str] = None
    host: Optional[str] = None
    routing_key: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None

    class Config:
        extra = "allow" 
        populate_by_name = True
        
class Message(BaseModel):
    detail: str
    system_metrics: dict