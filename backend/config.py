from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """
    它会自动从环境变量中读取配置，名字必须和变量名一致
    """
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DATABASE_URL: str
    ALLOW_ORIGINS: List[str]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # 方便别的文件导入