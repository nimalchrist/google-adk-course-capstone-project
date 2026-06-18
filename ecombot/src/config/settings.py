import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    pg_host: str = field(default_factory=lambda: os.getenv("PG_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("PG_PORT", "5432")))
    pg_db: str = field(default_factory=lambda: os.getenv("PG_DB", "ecombot"))
    pg_user: str = field(default_factory=lambda: os.getenv("PG_USER", "ecombot"))
    pg_password: str = field(default_factory=lambda: os.getenv("PG_PASSWORD", ""))


    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: str = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    redis_session_ttl: int = field(
        default_factory=lambda: int(os.getenv("REDIS_SESSION_TTL", "3600"))
    )

    orders_server_host: str = field(default_factory=lambda: os.getenv("ORDERS_SERVER_HOST", "127.0.0.1"))
    orders_server_port: int = field(default_factory=lambda: int(os.getenv("ORDERS_SERVER_PORT", "8766")))
    inventory_server_host: str = field(default_factory=lambda: os.getenv("INVENTORY_SERVER_HOST", "127.0.0.1"))
    inventory_server_port: int = field(default_factory=lambda: int(os.getenv("INVENTORY_SERVER_PORT", "8767")))

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def pg_dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} "
            f"dbname={self.pg_db} user={self.pg_user} "
            f"password={self.pg_password}"
        )

    @property
    def adk_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


settings = Settings()
