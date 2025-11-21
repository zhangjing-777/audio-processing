from sqlalchemy import Column, String, Integer, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ProcessingRecord(Base):
    """音频处理记录表"""
    __tablename__ = "processing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String, unique=True, index=True, nullable=False, comment="文件MD5哈希值")
    original_filename = Column(String, nullable=False, comment="原始文件名")
    service_type = Column(String, nullable=False, index=True, comment="服务类型: piano/spleeter/yourmt3")
    input_s3_url = Column(String, nullable=False, comment="输入音频S3 URL")
    output_s3_url = Column(String, comment="输出结果S3 URL")
    output_data = Column(JSON, comment="额外的输出数据(如spleeter的文件列表)")
    status = Column(String, default="processing", comment="状态: processing/completed/failed")
    runpod_job_id = Column(String, comment="RunPod任务ID")
    error_message = Column(String, comment="错误信息")
    processing_time = Column(Float, comment="处理时间(秒)")
    stems = Column(Integer, comment="Spleeter stems参数")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProcessingRecord(id={self.id}, file_hash={self.file_hash}, service_type={self.service_type})>"
