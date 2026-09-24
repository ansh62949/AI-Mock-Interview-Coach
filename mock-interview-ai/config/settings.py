import os
from pydantic import BaseModel
from dotenv import load_dotenv


# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)
load_dotenv()


class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    default_model: str = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_interview_turns: int = int(os.getenv("MAX_INTERVIEW_TURNS", "5"))
    
    # LangSmith Observability Configuration
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "true").lower() in ["true", "1", "t"]
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "HirePractice-AI")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


settings = Settings()
