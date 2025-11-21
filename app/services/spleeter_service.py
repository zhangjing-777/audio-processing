import httpx
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.config import get_settings
from app.models import ProcessingRecord
from app.services.s3_service import s3_service
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class SpleeterService:
    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint = settings.runpod_spleeter_endpoint
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"SpleeterService 初始化完成，端点: {self.endpoint}")
    
    async def check_existing_record(
        self,
        db: AsyncSession,
        file_hash: str,
        stems: int
    ) -> Optional[ProcessingRecord]:
        """检查是否已有处理记录(需要匹配stems参数)"""
        logger.info(f"检查是否存在缓存记录，file_hash: {file_hash}, stems: {stems}")
        query = select(ProcessingRecord).where(
            and_(
                ProcessingRecord.file_hash == file_hash,
                ProcessingRecord.service_type == "spleeter",
                ProcessingRecord.stems == stems,
                ProcessingRecord.status == "completed"
            )
        )
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            logger.info(f"✅ 找到缓存记录，ID: {record.id}, ZIP URL: {record.output_s3_url}")
        else:
            logger.info("未找到缓存记录")
        
        return record
    
    async def create_record(
        self,
        db: AsyncSession,
        file_hash: str,
        original_filename: str,
        input_s3_url: str,
        stems: int
    ) -> ProcessingRecord:
        """创建新的处理记录"""
        logger.info(f"创建数据库记录: file_hash={file_hash}, filename={original_filename}, stems={stems}")
        try:
            record = ProcessingRecord(
                file_hash=file_hash,
                original_filename=original_filename,
                service_type="spleeter",
                input_s3_url=input_s3_url,
                status="processing",
                stems=stems
            )
            db.add(record)
            await db.flush()
            await db.refresh(record)
            logger.info(f"✅ 数据库记录创建成功，ID: {record.id}")
            return record
        except Exception as e:
            logger.error(f"❌ 创建数据库记录失败: {e}", exc_info=True)
            await db.rollback()
            raise Exception(f"创建记录失败: {e}")
    
    async def process_audio(
        self,
        audio_url: str,
        stems: int = 2,
        format: str = "mp3",
        bitrate: str = "192k"
    ) -> Dict[str, Any]:
        """调用RunPod API处理音频"""
        payload = {
            "input": {
                "audio_url": audio_url,
                "stems": stems,
                "format": format,
                "bitrate": bitrate
            }
        }
        
        logger.info(f"发送请求到 RunPod API: {self.endpoint}")
        logger.debug(f"请求参数: {payload}")
        
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
                logger.info(f"✅ RunPod API 响应成功: {result}")
                return result
            except httpx.TimeoutException as e:
                logger.error(f"❌ RunPod API 请求超时: {e}")
                raise Exception(f"RunPod API 请求超时: {e}")
            except httpx.HTTPError as e:
                logger.error(f"❌ RunPod API HTTP错误: {e}, 响应内容: {e.response.text if hasattr(e, 'response') else 'N/A'}")
                raise Exception(f"RunPod API HTTP错误: {e}")
            except Exception as e:
                logger.error(f"❌ RunPod API 请求失败: {e}", exc_info=True)
                raise
    
    async def update_record_success(
        self,
        db: AsyncSession,
        record: ProcessingRecord,
        result: Dict[str, Any]
    ):
        """更新记录为成功状态"""
        logger.info(f"更新记录为成功状态，记录ID: {record.id}")
        output = result.get("output", {})
        record.status = "completed"
        record.output_s3_url = output.get("download_url")
        record.output_data = {
            "files": output.get("files", []),
            "size_mb": output.get("size_mb"),
            "bitrate": output.get("bitrate"),
            "format": output.get("format")
        }
        record.runpod_job_id = result.get("id")
        record.processing_time = (
            result.get("executionTime", 0) + result.get("delayTime", 0)
        ) / 1000.0
        await db.commit()
        await db.refresh(record)
        logger.info(f"✅ 记录更新成功，ZIP URL: {record.output_s3_url}, 处理时间: {record.processing_time}s")
    
    async def update_record_failure(
        self,
        db: AsyncSession,
        record: ProcessingRecord,
        error_message: str
    ):
        """更新记录为失败状态"""
        logger.warning(f"更新记录为失败状态，记录ID: {record.id}, 错误: {error_message}")
        record.status = "failed"
        record.error_message = error_message
        await db.commit()
        await db.refresh(record)
        logger.info(f"记录失败状态已保存")


# 创建全局实例
spleeter_service = SpleeterService()