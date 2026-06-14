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
    smtp_use_tls: bool = True
    google_client_id: str = ""
    trusted_hosts: str = ""
    run_startup_seeders: bool = True
    enable_in_process_worker: bool = False
    redis_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("mysql://"):
            return self.database_url.replace("mysql://", "mysql+pymysql://", 1)
        return self.database_url

    @property
    def smtp_login(self) -> str:
        return self.smtp_username or self.smtp_user

    @property
    def mail_from(self) -> str:
        return self.smtp_from_email or self.smtp_login

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    def validate_production_safety(self) -> None:
        if self.app_env != "production":
            return
        weak_secrets = {"", "change-this-secret-key", "test-secret"}
        if self.secret_key in weak_secrets or len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be a strong value in production")
        if not self.backend_cors_origins and not self.backend_cors_origin_regex:
            raise RuntimeError("Production CORS origins must be explicitly configured")


@lru_cache
def get_settings() -> Settings:
    return Settings()
