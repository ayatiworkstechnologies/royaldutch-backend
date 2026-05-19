from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClinicFlow API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/clinicflow"
    secret_key: str = "change-this-secret-key"
    access_token_expire_minutes: int = 1440
    backend_cors_origins: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Royal Dutch Medical Centre"
    smtp_use_ssl: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def smtp_login(self) -> str:
        return self.smtp_username or self.smtp_user

    @property
    def mail_from(self) -> str:
        return self.smtp_from_email or self.smtp_login


@lru_cache
def get_settings() -> Settings:
    return Settings()
