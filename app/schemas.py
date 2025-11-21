from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ServiceType(str, Enum):
    PIANO = "piano"
    SPLEETER = "spleeter"
    YOURMT3 = "yourmt3"


class ProcessingStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SpleeterStems(int, Enum):
    TWO = 2
    FOUR = 4
    FIVE = 5


# Piano 相关 Schema
class PianoTransRequest(BaseModel):
    pass  # 由 FastAPI 的 UploadFile 处理


class PianoTransResponse(BaseModel):
    status: str
    message: str
    midi_url: Optional[str] = None
    from_cache: bool = False
    job_id: Optional[str] = None


# Spleeter 相关 Schema
class SpleeterRequest(BaseModel):
    stems: SpleeterStems = Field(default=SpleeterStems.TWO, description="音轨数量: 2, 4, 或 5")
    format: str = Field(default="mp3", description="输出格式")
    bitrate: str = Field(default="192k", description="比特率")


class SpleeterFileInfo(BaseModel):
    name: str
    size_kb: float


class SpleeterResponse(BaseModel):
    status: str
    message: str
    download_url: Optional[str] = None
    files: Optional[List[SpleeterFileInfo]] = None
    size_mb: Optional[float] = None
    from_cache: bool = False
    job_id: Optional[str] = None


# YourMT3 相关 Schema
class YourMT3Request(BaseModel):
    pass  # 由 FastAPI 的 UploadFile 处理


class YourMT3Response(BaseModel):
    status: str
    message: str
    midi_url: Optional[str] = None
    from_cache: bool = False
    job_id: Optional[str] = None


# 通用响应
class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[str] = None


# 数据库记录 Schema
class ProcessingRecordSchema(BaseModel):
    id: int
    file_hash: str
    original_filename: str
    service_type: str
    input_s3_url: str
    output_s3_url: Optional[str]
    output_data: Optional[Dict[str, Any]]
    status: str
    processing_time: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
