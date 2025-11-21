from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import PianoTransResponse, ErrorResponse
from app.services import s3_service, piano_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/piano", tags=["Piano Transcription"])


@router.post("/transcribe", response_model=PianoTransResponse)
async def transcribe_piano(
    file: UploadFile = File(..., description="音频文件 (MP3/WAV/M4A)"),
    db: AsyncSession = Depends(get_db)
):
    """
    钢琴扒谱 API
    
    上传音频文件进行钢琴扒谱处理。如果该文件之前已处理过，将直接返回缓存结果。
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 计算文件哈希
        file_hash = s3_service.calculate_file_hash(file_content)
        
        # 检查是否已有处理记录
        existing_record = await piano_service.check_existing_record(db, file_hash)
        
        if existing_record and existing_record.output_s3_url:
            logger.info(f"找到缓存记录: {file_hash}")
            return PianoTransResponse(
                status="success",
                message="从缓存返回结果",
                midi_url=existing_record.output_s3_url,
                from_cache=True,
                job_id=existing_record.runpod_job_id
            )
        
        # 获取文件扩展名
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "mp3"
        
        # 上传到S3
        logger.info(f"开始上传文件到S3，文件大小: {len(file_content)} bytes, 文件名：{file.filename}")
        s3_url, _ = await s3_service.upload_file(
            file_content=file_content,
            folder="url2mp3",
            extension=file_extension,
            content_type=file.content_type or "audio/mpeg"
        )
        logger.info(f"S3上传完成: {s3_url}")
        
        # 创建处理记录
        record = await piano_service.create_record(
            db=db,
            file_hash=file_hash,
            original_filename=file.filename,
            input_s3_url=s3_url
        )
        
        # 调用RunPod API
        logger.info(f"调用RunPod API处理: {s3_url}")
        try:
            result = await piano_service.process_audio(s3_url)
            logger.info(f"RunPod API 返回结果: {result}")
            # 检查处理状态
            if result.get("status") == "COMPLETED":
                await piano_service.update_record_success(db, record, result)
                
                midi_url = result.get("output", {}).get("midi_url")
                return PianoTransResponse(
                    status="success",
                    message="钢琴扒谱完成",
                    midi_url=midi_url,
                    from_cache=False,
                    job_id=result.get("id")
                )
            else:
                error_msg = f"RunPod任务状态异常: {result.get('status')}"
                await piano_service.update_record_failure(db, record, error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
                
        except Exception as e:
            error_msg = f"RunPod API调用失败: {str(e)}"
            logger.error(error_msg)
            await piano_service.update_record_failure(db, record, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "piano"}
