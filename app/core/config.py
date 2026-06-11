from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Royal Dutch Medical Centre API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/royaldutch"
    database_ssl: bool = False
    database_ssl_ca_path: str = ""
    database_ssl_verify_identity: bool = False
    secret_key: str = "change-this-secret-key"
    access_token_expire_minutes: int = 1440
    backend_cors_origins: str = ""
    backend_cors_origin_regex: str = r"https://.*\.vercel\.app"
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
    def sqlalchemy_database_url(self) -> str:
        # FORCE TiDB connection string to bypass bad Render environment variables
        forced_url = "mysql+pymysql://4WNyZSBMUeNx4G6.root:Ybzbtzi7a0qDnNJr@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/royaldutch"
        if forced_url.startswith("mysql://"):
            return forced_url.replace("mysql://", "mysql+pymysql://", 1)
        return forced_url

    @property
    def smtp_login(self) -> str:
        return self.smtp_username or self.smtp_user

    @property
    def mail_from(self) -> str:
        return self.smtp_from_email or self.smtp_login


@lru_cache
def get_settings() -> Settings:
    return Settings()
