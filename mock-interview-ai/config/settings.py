import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    default_model: str = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_interview_turns: int = int(os.getenv("MAX_INTERVIEW_TURNS", "5"))


settings = Settings()
