from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Uygulama ayarlarını temsil eden Pydantic sınıfı.
    Varsayılan değerler tanımlanabilir veya .env dosyasından otomatik okunur.
    """
    # Genel Uygulama Ayarları
    PROJECT_NAME: str = "Agentic Code Reviewer & Guardrail Evaluator"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # LLM API Keys
    GROQ_API_KEY: str = ""

    # Veritabanı (PostgreSQL) Ayarları
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "code_reviewer_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # Cache (Redis) Ayarları
    REDIS_URL: str = "redis://localhost:6379/0"

    # GitHub Webhook & Entegrasyon Ayarları
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # .env dosyasından okuma konfigürasyonu
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()