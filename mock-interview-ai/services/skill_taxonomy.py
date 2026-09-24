import re
from typing import Dict, List, Set, Optional

# 1. Canonical Skill Aliases
CANONICAL_SKILL_ALIASES: Dict[str, str] = {
    # DevOps / Cloud / Containers / CI-CD / IaC
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud platform": "GCP",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "terraform": "Terraform",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "gitlab-ci": "GitLab CI",
    "docker": "Docker",
    "docker compose": "Docker Compose",
    "ansible": "Ansible",
    "helm": "Helm",

    # Scripting & Languages
    "python": "Python",
    "py": "Python",
    "bash": "Bash",
    "sh": "Bash",
    "shell": "Bash",
    "powershell": "PowerShell",
    "ps": "PowerShell",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "cpp": "C++",
    "c++": "C++",
    "c": "C",

    # Frameworks
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "spring boot 3": "Spring Boot",
    "spring boot 3.5": "Spring Boot",
    "spring security": "Spring Security",
    "fastapi": "FastAPI",
    "react": "React",
    "react.js": "React",
    "node": "Node.js",
    "node.js": "Node.js",

    # Databases & Storage
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "pgvector": "pgvector",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "redis geo": "Redis",

    # Messaging & Distributed Systems
    "kafka": "Apache Kafka",
    "apache kafka": "Apache Kafka",
    "rabbitmq": "RabbitMQ",
    "eureka": "Eureka",
    "microservices": "Microservices",
    "event-driven architecture": "Event-Driven Architecture",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "websockets": "WebSockets",
    "stomp": "WebSockets",

    # Version Control
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",

    # Operating Systems
    "linux": "Linux",
    "unix": "Linux/Unix",
    "linux/unix": "Linux/Unix",
    "ubuntu": "Linux",
    "debian": "Linux",

    # Networking
    "tcp/ip": "TCP/IP",
    "networking": "Networking",
    "dns": "DNS",
    "ssh": "SSH",
    "http": "HTTP",
    "https": "HTTP",

    # AI & ML
    "langgraph": "LangGraph",
    "rag": "RAG",
    "llm": "LLM",
    "vector database": "Vector Database"
}

# 2. Internal Skill Taxonomy (Categories)
# Note: Category membership is NOT proof of possession.
SKILL_TAXONOMY: Dict[str, List[str]] = {
    "DevOps": ["Docker", "Docker Compose", "Kubernetes", "Terraform", "Jenkins", "GitHub Actions", "GitLab CI", "AWS", "Azure", "GCP", "Ansible", "Helm"],
    "Operating Systems": ["Linux", "Linux/Unix", "Windows"],
    "Scripting": ["Python", "Bash", "PowerShell"],
    "Networking": ["Networking", "TCP/IP", "DNS", "HTTP", "SSH"],
    "Version Control": ["Git", "GitHub", "GitLab", "Bitbucket"],
    "Languages": ["Java", "Python", "JavaScript", "TypeScript", "C++", "C"],
    "Frameworks": ["Spring Boot", "Spring Security", "FastAPI", "React", "Node.js"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "pgvector"],
    "Containers": ["Docker", "Docker Compose", "Kubernetes"],
    "CI_CD": ["Jenkins", "GitHub Actions", "GitLab CI"],
    "Messaging": ["Apache Kafka", "RabbitMQ", "Redis", "Eureka"],
    "AI_ML": ["LangGraph", "RAG", "LLM", "Vector Database", "pgvector"]
}


def normalize_skill_name(skill_str: str) -> str:
    """Normalizes raw skill strings into their canonical skill names."""
    clean = skill_str.strip().lower().rstrip(":-_#* ")
    if clean in CANONICAL_SKILL_ALIASES:
        return CANONICAL_SKILL_ALIASES[clean]
    
    for alias, canonical in CANONICAL_SKILL_ALIASES.items():
        if alias == clean or clean == canonical.lower():
            return canonical

    return skill_str.strip().title()
