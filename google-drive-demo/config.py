from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # S3 config
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "google-drive-demo-bucket"
    s3_endpoint_url: str = ""  # For LocalStack: http://localhost:4566

    # DB
    database_url: str = "sqlite:///./gdrive_demo.db"

    # Presigned URLs
    presigned_url_expiry_seconds: int = 3600  # 1 hour

    class Config:
        env_file = ".env"


settings = Settings()
