import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from config.settings import settings
from utils.logger import logger


def setup_langsmith_tracing() -> None:
    """Configures LangSmith observability parameters safely without blocking execution."""
    langsmith_key = os.getenv("LANGSMITH_API_KEY") or settings.langsmith_api_key
    if langsmith_key and langsmith_key != "your_langsmith_api_key_here":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGCHAIN_API_KEY"] = langsmith_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info(f"LangSmith Tracing enabled for project '{settings.langsmith_project}'.")
    else:
        # Fail-safe non-blocking execution
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


def get_llm(temperature: Optional[float] = None, timeout: Optional[float] = 15.0, max_retries: int = 1) -> Optional[BaseChatModel]:
    """
    Factory function returning configured LLM instance (Groq, OpenAI, or Gemini).
    Returns None if no API key is set, enabling offline fallback execution.
    """
    setup_langsmith_tracing()
    model_temperature = settings.temperature if temperature is None else temperature
    
    groq_api_key = os.getenv("GROQ_API_KEY") or settings.groq_api_key
    openai_api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key

    # Check for Groq API key first
    if groq_api_key and groq_api_key.startswith("gsk_"):
        from langchain_groq import ChatGroq
        model_name = settings.default_model if settings.default_model not in ["llama-3.3-70b-versatile", "llama3-8b-8192", "llama-3.1-8b-instant"] else "qwen/qwen3.8-27b"
        logger.info(f"Initializing ChatGroq client with model '{model_name}'.")
        return ChatGroq(
            model=model_name,
            temperature=model_temperature,
            api_key=groq_api_key,
            max_tokens=800,
            request_timeout=timeout,
            max_retries=max_retries
        )

    # Check for standard OpenAI API key
    if openai_api_key and openai_api_key != "your_openai_api_key_here":
        if openai_api_key.startswith("gsk_"):
            from langchain_openai import ChatOpenAI
            logger.info("Initializing Groq ChatOpenAI client via OpenAI key setting.")
            return ChatOpenAI(
                model="llama-3.3-70b-versatile",
                temperature=model_temperature,
                api_key=openai_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            from langchain_openai import ChatOpenAI
            logger.info(f"Initializing OpenAI ChatOpenAI client with model '{settings.default_model}'.")
            return ChatOpenAI(
                model=settings.default_model,
                temperature=model_temperature,
                api_key=openai_api_key
            )
            
    # Check for Gemini API key
    if google_api_key and google_api_key != "your_google_api_key_here":
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.info("Initializing Google Gemini Chat model.")
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=model_temperature,
            google_api_key=google_api_key
        )
    
    logger.info("No LLM API key detected in environment. Using offline fallback mode.")
    return None
