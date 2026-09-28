from pydantic import BaseModel


class Settings(BaseModel):
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    active_replay_event: str = "bhubaneswar-synthetic-001"


settings = Settings()
