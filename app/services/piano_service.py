import httpx
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models import ProcessingRecord
from app.services.s3_service import s3_service
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class PianoTransService:
    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint = settings.runpod_piano_endpoint
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def check_existing_record(
        self,
        db: AsyncSession,
        file_hash: str
    ) -> Optional[ProcessingRecord]:
        """检查是否已有处理记录"""
        query = select(ProcessingRecord).where(
            ProcessingRecord.file_hash == file_hash,
            ProcessingRecord.service_type == "piano",
            ProcessingRecord.status == "completed"
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_record(
        self,
        db: AsyncSession,
        file_hash: str,
        original_filename: str,
        input_s3_url: str
    ) -> ProcessingRecord:
        """创建新的处理记录"""
        record = ProcessingRecord(
            file_hash=file_hash,
            original_filename=original_filename,
            service_type="piano",
            input_s3_url=input_s3_url,
            status="processing"
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    
    async def process_audio(
        self,
        audio_url: str
    ) -> Dict[str, Any]:
        """调用RunPod API处理音频"""
        payload = {
            "input": {
                "audio_url": audio_url
            }
        }
        
        logger.info(f"发送请求到 RunPod API: {self.endpoint}")
        logger.info(f"请求参数: {payload}")
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            try:
                response = await client.post(
                    self.endpoint,
                    headers=self.headers,
                    json=payload
                )
                logger.info(f"RunPod API 响应状态码: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                logger.info(f"RunPod API 响应: {result}")
                return result
            except httpx.TimeoutException as e:
                logger.error(f"RunPod API 请求超时: {e}")
                raise Exception(f"RunPod API 请求超时: {e}")
            except httpx.HTTPError as e:
                logger.error(f"RunPod API HTTP错误: {e}")
                raise Exception(f"RunPod API HTTP错误: {e}")
            except Exception as e:
                logger.error(f"RunPod API 请求失败: {e}")
                raise
    
    async def update_record_success(
        self,
        db: AsyncSession,
        record: ProcessingRecord,
        result: Dict[str, Any]
    ):
        """更新记录为成功状态"""
        record.status = "completed"
        record.output_s3_url = result.get("output", {}).get("midi_url")
        record.runpod_job_id = result.get("id")
        record.processing_time = (
            result.get("executionTime", 0) + result.get("delayTime", 0)
        ) / 1000.0  # 转换为秒
        await db.commit()
        await db.refresh(record)
    
    async def update_record_failure(
        self,
        db: AsyncSession,
        record: ProcessingRecord,
        error_message: str
    ):
        """更新记录为失败状态"""
        record.status = "failed"
        record.error_message = error_message
        await db.commit()
        await db.refresh(record)


# 创建全局实例
piano_service = PianoTransService()