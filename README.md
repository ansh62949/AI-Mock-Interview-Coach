# 🎯 HirePractice AI — AI Mock Interview & Adaptive Career Coach

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG%20Store-purple.svg)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **From Resume Parsing & Job Description Matching to Adaptive ReAct Mock Interviews with 5-State Answer Classification.**

HirePractice AI is a production-oriented AI SaaS platform built with **LangGraph**, **FastAPI**, **ChromaDB RAG**, and **Streamlit**. It transforms raw candidate resumes and job descriptions into explainable match gap reports, targeted cold outreach emails, personalized interview roadmaps, and **adaptive AI technical interviews** that intelligently respond to candidate knowledge states.

---

## 🌟 Key Features

- **5-State Answer Classification Engine**:
  Classifies candidate responses into **5 distinct answer states**:
  - `unknown`: Triggers `teach_then_probe` adaptive follow-ups (*"No problem. Let's break it down..."*)
  - `incorrect`: Targets specific misconceptions (*"You mentioned X..."*)
  - `partial`: Probes missing concepts
  - `correct`: Increases question difficulty and technical depth
  - `off_topic`: Gently redirects back to the core technical question
- **ReAct-Style Agentic Tool Calling**:
  Real LLM tool execution loop where the Interviewer agent decides when to query the **ChromaDB vector store** (`search_interview_questions`) based on candidate performance and target skill gaps.
- **Safe Agent Activity UI Trace**:
  Renders clean, candidate-safe execution activity summaries in a collapsible expander (e.g., *"Checking question bank..."*, *"Targeting a knowledge gap..."*) without revealing raw chain-of-thought logic.
- **Explainable Resume-to-JD Match Engine**:
  Calculates a transparent match score (0–100%) with explicit breakdown: Required Skill Coverage (35%), Project Relevance (25%), Experience (20%), Preferred Skills (10%), and Education (10%).
- **Personalized 6-Round Interview Blueprint**:
  Generates a structured multi-round roadmap tailored to detected candidate skill gaps.
- **Automated Resume & JD Parsers**:
  Extracts candidate technical stack, experience, and projects alongside sanitized JD roles with zero prompt dumping.
- **Personalized Cold Outreach Email Generator**:
  Creates tailored job application email drafts based on resume + JD context with one-click copy.
- **SQLite History & Skill Analytics**:
  Saves interview sessions and tracks candidate performance improvement across technical skill categories over time.
- **LangSmith Observability**:
  Full tracing across LangGraph state execution, LLM calls, and tool invocations.

---

## 📸 Application Screenshots

| 🏠 Resume & JD Setup | 📊 Match Analysis |
| :---: | :---: |
| ![Resume & JD Setup](docs/screenshots/resume_jd_setup.png) | ![Match Analysis](docs/screenshots/match_analysis.png) |

| 🎯 6-Round Blueprint | 💬 Adaptive AI Interview |
| :---: | :---: |
| ![Interview Blueprint](docs/screenshots/interview_blueprint.png) | ![Adaptive AI Interview](docs/screenshots/active_interview.png) |

| 📈 Category Progress | 📜 Session History |
| :---: | :---: |
| ![Category Progress](docs/screenshots/progress.png) | ![Session History](docs/screenshots/history.png) |

---

## 🏛️ Adaptive ReAct Architecture

```mermaid
flowchart TD
    A[Candidate Response] --> B[5-State Answer Classifier]
    
    B -->|Unknown| C1[teach_then_probe]
    B -->|Incorrect| C2[target_misconception]
    B -->|Partial| C3[probe_missing_concept]
    B -->|Correct| C4[increase_depth]
    B -->|Off-Topic| C5[redirect]
    
    C1 & C2 & C3 & C4 & C5 --> D[ReAct Agent Decision Engine]
    D -->|Tool Call| E[search_interview_questions]
    E --> F[ChromaDB Vector Store]
    F -->|Retrieved Concepts| D
    D --> G[Adaptive Next Question]
    G --> H[Agent Activity UI Summary]
```

---

## 📊 5-State Classification Matrix

| Candidate Response | Answer Status | Evaluation Output | Adaptive Next Action |
| :--- | :--- | :--- | :--- |
| *"I don't know."* | `unknown` | `tech_score: 1`, `followup_strategy: teach_then_probe` | Breaks concept down into scenario-based learning probe |
| *"Lambda is cheaper and ECS doesn't scale."* | `incorrect` | `misconceptions: ["ECS can scale"]`, `followup_strategy: target_misconception` | Probes specific misconception with auto-scaling context |
| *"Lambda auto-scales, but ECS takes longer."* | `partial` | `knowledge_gaps: ["Cold starts vs task provisioning"]` | Asks probing question on missing concept |
| *"Lambda scales with requests, ECS uses task scaling policies..."* | `correct` | `depth_score: 8`, `followup_strategy: increase_depth` | Increases technical complexity & operational tradeoffs |
| *"I prefer working in Python for web dev."* | `off_topic` | `relevance_score: 1`, `followup_strategy: redirect` | Refocuses candidate on current question |

---

## 🏗️ Technical Architecture & Multi-Agent Graph

```mermaid
flowchart LR
    subgraph Frontend & API
        UI[Streamlit SaaS UI] <--> API[FastAPI Backend]
    end
    
    subgraph Core Services
        API --> Parser[Resume & JD Parsers]
        API --> Matcher[Match Engine]
        API --> ColdEmail[Cold Email Generator]
    end
    
    subgraph LangGraph Workflow
        API --> Graph[LangGraph StateGraph]
        Graph --> Planner[Planner Agent]
        Graph --> Interviewer[Interviewer Agent + ReAct Tools]
        Graph --> Evaluator[5-State Evaluator]
        Graph --> Reflection[Reflection Router]
        Graph --> Coach[Executive Coach Agent]
    end
    
    subgraph Data & Storage
        Interviewer <--> VectorDB[(ChromaDB RAG)]
        Graph --> HistoryDB[(SQLite History & Analytics)]
    end
```

---

## 💻 Tech Stack

- **Frameworks & Multi-Agent**: [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain)
- **LLM Infrastructure**: Groq API (`llama-3.3-70b-versatile`), OpenAI (`gpt-4o-mini`), Google Gemini
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, Pydantic V2
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) (RAG concept & question retrieval)
- **Frontend UI**: [Streamlit](https://streamlit.io/) (Clean Slate/Indigo SaaS layout)
- **Storage & Parsers**: SQLite3, pdfplumber, python-docx
- **Observability & Testing**: LangSmith, Pytest (100% pass rate across unit/integration tests)

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Groq or OpenAI API key

### 2. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/ansh62949/AI-Mock-Interview-Coach.git
cd AI-Mock-Interview-Coach/mock-interview-ai

# Create virtual environment & install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY or OPENAI_API_KEY
```

### 3. Run Application

```bash
# Terminal 1: Start FastAPI Backend Server
py -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Streamlit Frontend Dashboard
py -m streamlit run ui/app.py --server.port 8501
```

Open your browser at:
- **SaaS Dashboard**: [http://localhost:8501](http://localhost:8501)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🐳 Running with Docker

```bash
# Build and run containers
docker-compose up --build
```

- Streamlit UI: `http://localhost:8501`
- FastAPI Server: `http://localhost:8000`

---

## 🧪 Running Automated Tests

Run the comprehensive test suite:

```bash
py -m pytest mock-interview-ai/tests -v
```

---

## 📁 Repository Structure

```text
AI-Mock-Interview-Coach/
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── README.md
└── mock-interview-ai/
    ├── agents/             # LangGraph Agents (Planner, Interviewer, Evaluator, Reflection, Coach)
    ├── database/           # SQLite Database & Session Persistence
    ├── graph/              # LangGraph Workflow State & Graph Definition
    ├── prompts/            # Agent Prompt Templates & System Prompts
    ├── rag/                # ChromaDB Vector Store & Retriever
    ├── schemas/            # Pydantic V2 Models & Data Schemas
    ├── services/           # Resume/JD Parsers, Match Engine, Cold Email, Tools
    ├── tests/              # Pytest Unit & Integration Suite
    ├── tools/              # ReAct Agent Tools (RAG Retrieval, Verification)
    ├── ui/                 # Streamlit UI SaaS Application
    ├── main.py             # FastAPI REST Server
    ├── requirements.txt    # Python Dependencies
    └── README.md           # Detailed Component Documentation
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
