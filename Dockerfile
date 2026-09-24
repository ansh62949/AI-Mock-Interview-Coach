# Use official lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies manifest
COPY mock-interview-ai/requirements.txt /app/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY mock-interview-ai/ /app/

# Expose FastAPI (8000) and Streamlit (8501) ports
EXPOSE 8000 8501

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Command default launches FastAPI server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
