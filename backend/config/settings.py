from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # MongoDB Configuration
    MONGO_URL: str = Field(default="mongodb://127.0.0.1:27017/acciones_ml", description="MongoDB Connection URL")
    MONGO_INITDB_ROOT_USERNAME: str = Field(default="root", description="MongoDB Root Username")
    MONGO_INITDB_ROOT_PASSWORD: str = Field(default="example", description="MongoDB Root Password")

    # API Configuration
    SECRET_KEY: str = Field(default="your-secret-key-here", description="Secret key for JWT")
    ALGORITHM: str = Field(default="HS256", description="Algorithm used for JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Token expiration time in minutes")
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Execution environment (development, staging, production)")

    # Model Configuration
    MODEL_DIR: str = Field(default="../ml/models", description="Directory where .pkl models are stored")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
