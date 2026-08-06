import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from config.settings import settings
from utils.logger import logger


def get_llm(temperature: Optional[float] = None) -> Optional[BaseChatModel]:
    """
    Factory function returning configured LLM instance (Groq, OpenAI, or Gemini).
    Returns None if no API key is set, enabling offline fallback execution.
    """
    model_temperature = settings.temperature if temperature is None else temperature
    
    groq_api_key = os.getenv("GROQ_API_KEY") or settings.groq_api_key
    openai_api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key

    # Check for Groq API key first
    if groq_api_key and groq_api_key.startswith("gsk_"):
        from langchain_openai import ChatOpenAI
        model_name = settings.default_model if "llama" in settings.default_model or "mixtral" in settings.default_model else "llama-3.3-70b-versatile"
        logger.info(f"Initializing Groq ChatOpenAI client with model '{model_name}'.")
        return ChatOpenAI(
            model=model_name,
            temperature=model_temperature,
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
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
