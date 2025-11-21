from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import YourMT3Response, ErrorResponse
from app.services import s3_service, yourmt3_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/yourmt3", tags=["YourMT3"])


@router.post("/transcribe", response_model=YourMT3Response)
async def transcribe_multitrack(
    file: UploadFile = File(..., description="音频文件 (MP3/WAV/M4A)"),
    db: AsyncSession = Depends(get_db)
):
    """多轨扒谱 API"""
    logger.info(f"========== 开始多轨扒谱请求 ==========")
    logger.info(f"文件名: {file.filename}, Content-Type: {file.content_type}")
    
    try:
        # 读取文件内容
        logger.info("读取上传文件内容...")
        file_content = await file.read()
        logger.info(f"文件读取完成，大小: {len(file_content)} bytes ({len(file_content)/1024/1024:.2f} MB)")
        
        # 计算文件哈希
        file_hash = s3_service.calculate_file_hash(file_content)
        logger.info(f"文件哈希: {file_hash}")
        
        # 检查是否已有处理记录
        existing_record = await yourmt3_service.check_existing_record(db, file_hash)
        
        if existing_record and existing_record.output_s3_url:
            logger.info(f"✅ 找到缓存记录，直接返回结果")
            return YourMT3Response(
                status="success",
                message="从缓存返回结果",
                midi_url=existing_record.output_s3_url,
                from_cache=True,
                job_id=existing_record.runpod_job_id
            )
        
        # 获取文件扩展名
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "mp3"
        logger.info(f"文件扩展名: {file_extension}")
        
        # 上传到S3
        s3_url, _ = await s3_service.upload_file(
            file_content=file_content,
            folder="url2mp3",
            extension=file_extension,
            content_type=file.content_type or "audio/mpeg"
        )
        
        # 创建处理记录
        record = await yourmt3_service.create_record(
            db=db,
            file_hash=file_hash,
            original_filename=file.filename,
            input_s3_url=s3_url
        )
        
        # 提交事务
        await db.commit()
        logger.info("数据库事务已提交")
        
        # 调用RunPod API
        try:
            result = await yourmt3_service.process_audio(s3_url)
            
            # 检查处理状态
            if result.get("status") == "COMPLETED":
                await yourmt3_service.update_record_success(db, record, result)
                
                midi_url = result.get("output", {}).get("midi_url")
                logger.info(f"========== 多轨扒谱请求完成 ==========")
                return YourMT3Response(
                    status="success",
                    message="多轨扒谱完成",
                    midi_url=midi_url,
                    from_cache=False,
                    job_id=result.get("id")
                )
            else:
                error_msg = f"RunPod任务状态异常: {result.get('status')}"
                await yourmt3_service.update_record_failure(db, record, error_msg)
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
                
        except Exception as e:
            error_msg = f"RunPod API调用失败: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            await yourmt3_service.update_record_failure(db, record, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "yourmt3"}