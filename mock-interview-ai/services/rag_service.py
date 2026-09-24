import os
import json
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from utils.logger import logger

# Path for ChromaDB persistence
CHROMA_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "chromadb"))


class RAGService:
    """ChromaDB Vector Storage and RAG Retrieval Engine for HirePractice AI."""

    def __init__(self, persist_dir: str = CHROMA_DATA_PATH) -> None:
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Initialize collections
        self.questions_col = self.client.get_or_create_collection(name="interview_questions")
        self.knowledge_col = self.client.get_or_create_collection(name="technical_knowledge")
        self.candidate_col = self.client.get_or_create_collection(name="candidate_context")
        
        # Seed questions if collection is empty
        self._seed_question_bank_if_needed()

    def _seed_question_bank_if_needed(self) -> None:
        """Seeds initial domain question bank into ChromaDB if empty."""
        try:
            if self.questions_col.count() > 0:
                return
        except Exception:
            pass

        logger.info("RAGService: Seeding ChromaDB interview question bank...")
        seed_questions = [
            # Technical - Backend & Java/Python
            {"id": "q1", "topic": "Java", "difficulty": "Mid-Level", "text": "Explain the difference between HashMap, ConcurrentHashMap, and Hashtable in Java. How is thread safety achieved?"},
            {"id": "q2", "topic": "Java", "difficulty": "Senior", "text": "How does Java Garbage Collection work under the hood? Compare G1GC with ZGC in terms of pause times and heap sizing."},
            {"id": "q3", "topic": "Python", "difficulty": "Mid-Level", "text": "Explain how Python's GIL (Global Interpreter Lock) impacts multi-threading vs multi-processing for CPU-bound tasks."},
            {"id": "q4", "topic": "Spring Boot", "difficulty": "Mid-Level", "text": "What is Dependency Injection in Spring Boot? Compare Field Injection with Constructor Injection and explain circular dependencies."},
            {"id": "q5", "topic": "REST APIs", "difficulty": "Junior", "text": "What are the core principles of REST architecture? Compare GET, POST, PUT, and PATCH HTTP methods."},
            
            # Databases & SQL
            {"id": "q6", "topic": "SQL", "difficulty": "Mid-Level", "text": "Explain the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN. How do database indexes speed up JOIN queries?"},
            {"id": "q7", "topic": "DBMS", "difficulty": "Senior", "text": "What are ACID properties in database management systems? How do database isolation levels prevent phantom reads and dirty reads?"},
            {"id": "q8", "topic": "Redis", "difficulty": "Mid-Level", "text": "How is Redis used for caching and pub/sub messaging? What eviction policies does Redis support when memory limits are reached?"},
            {"id": "q9", "topic": "Kafka", "difficulty": "Senior", "text": "How do Kafka topic partitions, consumer groups, and offsets guarantee message ordering and scalability?"},

            # AI & LLM Engineering
            {"id": "q10", "topic": "RAG", "difficulty": "Senior", "text": "Walk me through the architecture of a Retrieval-Augmented Generation (RAG) system. How do chunk size and embedding models impact retrieval precision?"},
            {"id": "q11", "topic": "LLMs", "difficulty": "Mid-Level", "text": "What is the difference between fine-tuning a model vs prompt engineering with RAG? When would you choose one over the other?"},
            {"id": "q12", "topic": "Vector DBs", "difficulty": "Mid-Level", "text": "How does vector similarity search work (Cosine Similarity vs HNSW indexing)? Why are vector stores critical for LLM context grounding?"},

            # System Design & Architecture
            {"id": "q13", "topic": "System Design", "difficulty": "Senior", "text": "How would you design a scalable URL shortener service like Bitly capable of handling 100 million active daily users?"},
            {"id": "q14", "topic": "Docker", "difficulty": "Mid-Level", "text": "Explain the difference between Docker images and containers. How do multi-stage Docker builds optimize image size for production?"},
            {"id": "q15", "topic": "AWS", "difficulty": "Senior", "text": "Compare AWS Lambda serverless execution with ECS container deployment for microservices in terms of latency, scaling, and cost."}
        ]

        documents = [q["text"] for q in seed_questions]
        ids = [q["id"] for q in seed_questions]
        metadatas = [{"topic": q["topic"], "difficulty": q["difficulty"]} for q in seed_questions]

        self.questions_col.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"RAGService: Successfully seeded {len(seed_questions)} questions into ChromaDB.")

    def retrieve_relevant_context(self, query: str, topic: Optional[str] = None, limit: int = 3) -> List[str]:
        """Retrieves relevant question templates and technical concepts from ChromaDB."""
        try:
            where_clause = {"topic": topic} if topic else None
            results = self.questions_col.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause
            )
            if results and results.get("documents") and len(results["documents"]) > 0:
                return results["documents"][0]
        except Exception as e:
            logger.warning(f"RAGService: ChromaDB query fallback: {e}")

        return [
            f"Core conceptual question on {topic if topic else 'Software Architecture'}",
            "Follow up on system trade-offs, edge cases, and practical implementation details."
        ]

    def store_candidate_context(self, session_id: str, context_text: str) -> None:
        """Indexes candidate resume + JD context for session grounding."""
        try:
            self.candidate_col.add(
                documents=[context_text[:2000]],
                ids=[f"session_{session_id}"],
                metadatas=[{"session_id": session_id}]
            )
        except Exception as e:
            logger.warning(f"RAGService: Failed to index session context: {e}")


rag_service = RAGService()
