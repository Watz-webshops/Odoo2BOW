from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://odoo2bow:changeme@localhost:5432/odoo2bow"
    secret_key: str = "insecure-dev-secret-change-in-production"
    admin_jwt_secret: str = "insecure-jwt-secret-change-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    log_level: str = "INFO"
    max_participations_per_export: int = 50_000
    api_version: str = "v1"


settings = Settings()
