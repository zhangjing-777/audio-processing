from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AWS S3 配置
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-southeast-1"
    s3_bucket_name: str = "qiupupu"
    
    # 数据库配置
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int = 5432
    
    # RunPod API 配置
    runpod_api_key: str
    runpod_piano_endpoint: str
    runpod_spleeter_endpoint: str
    runpod_yourmt3_endpoint: str
    
    # 应用配置
    app_name: str = "Audio Processing API"
    debug: bool = False
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
