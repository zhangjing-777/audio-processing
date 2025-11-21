from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import SpleeterResponse, SpleeterStems, SpleeterFileInfo
from app.services import s3_service, spleeter_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spleeter", tags=["Spleeter"])


@router.post("/separate", response_model=SpleeterResponse)
async def separate_audio(
    file: UploadFile = File(..., description="音频文件 (MP3/WAV/M4A)"),
    stems: int = Form(default=2, description="音轨数量: 2, 4, 或 5"),
    format: str = Form(default="mp3", description="输出格式"),
    bitrate: str = Form(default="192k", description="比特率"),
    db: AsyncSession = Depends(get_db)
):
    """音频分离 API"""
    logger.info(f"========== 开始音频分离请求 ==========")
    logger.info(f"文件名: {file.filename}, stems: {stems}, format: {format}, bitrate: {bitrate}")
    
    try:
        # 验证stems参数
        if stems not in [2, 4, 5]:
            logger.error(f"stems参数无效: {stems}")
            raise HTTPException(status_code=400, detail="stems参数必须是 2, 4 或 5")
        
        # 读取文件内容
        logger.info("读取上传文件内容...")
        file_content = await file.read()
        logger.info(f"文件读取完成，大小: {len(file_content)} bytes ({len(file_content)/1024/1024:.2f} MB)")
        
        # 计算文件哈希
        file_hash = s3_service.calculate_file_hash(file_content)
        logger.info(f"文件哈希: {file_hash}")
        
        # 检查是否已有处理记录
        existing_record = await spleeter_service.check_existing_record(db, file_hash, stems)
        
        if existing_record and existing_record.output_s3_url:
            logger.info(f"✅ 找到缓存记录，直接返回结果")
            files_info = []
            if existing_record.output_data:
                files_data = existing_record.output_data.get("files", [])
                files_info = [SpleeterFileInfo(**f) for f in files_data]
            
            return SpleeterResponse(
                status="success",
                message="从缓存返回结果",
                download_url=existing_record.output_s3_url,
                files=files_info,
                size_mb=existing_record.output_data.get("size_mb") if existing_record.output_data else None,
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
        record = await spleeter_service.create_record(
            db=db,
            file_hash=file_hash,
            original_filename=file.filename,
            input_s3_url=s3_url,
            stems=stems
        )
        
        # 提交事务
        await db.commit()
        logger.info("数据库事务已提交")
        
        # 调用RunPod API
        try:
            result = await spleeter_service.process_audio(
                audio_url=s3_url,
                stems=stems,
                format=format,
                bitrate=bitrate
            )
            
            # 检查处理状态
            if result.get("status") == "COMPLETED":
                await spleeter_service.update_record_success(db, record, result)
                
                output = result.get("output", {})
                files_data = output.get("files", [])
                files_info = [SpleeterFileInfo(**f) for f in files_data]
                
                logger.info(f"========== 音频分离请求完成 ==========")
                return SpleeterResponse(
                    status="success",
                    message="音频分离完成",
                    download_url=output.get("download_url"),
                    files=files_info,
                    size_mb=output.get("size_mb"),
                    from_cache=False,
                    job_id=result.get("id")
                )
            else:
                error_msg = f"RunPod任务状态异常: {result.get('status')}"
                await spleeter_service.update_record_failure(db, record, error_msg)
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
                
        except Exception as e:
            error_msg = f"RunPod API调用失败: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            await spleeter_service.update_record_failure(db, record, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "spleeter"}