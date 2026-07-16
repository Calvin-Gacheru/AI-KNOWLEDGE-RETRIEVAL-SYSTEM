# AI-Powered Knowledge Retrieval System

## 1. Project Overview

The AI-Powered Knowledge Retrieval System is a full-stack, Retrieval-Augmented Generation (RAG) application designed to streamline technical support operations. Technical support teams frequently face information silos, where data is fragmented across legacy wikis, scattered PDFs, and emails. This leads to search inefficiency and knowledge decay, severely impacting ticket resolution times.

This system resolves these bottlenecks by centralizing technical documentation into a vector database and providing a semantic search interface. Instead of relying on rigid keyword matching, the application understands natural language queries, retrieves the most mathematically relevant documentation, and leverages a Large Language Model (LLM) to generate instant, context-aware, and verified solutions.

## 2. System Architecture & Tech Stack

The architecture is designed for low latency, local embedding processing, and unified relational/vector data storage.

* **Frontend:** HTML5, Tailwind CSS (via CDN), Vanilla JavaScript.
* **Backend Application:** Python, FastAPI, Uvicorn.
* **Database Engine:** PostgreSQL.
* **Vector Store:** `pgvector` (PostgreSQL extension).
* **Object-Relational Mapping (ORM):** SQLAlchemy.
* **AI/RAG Orchestration:** LangChain.
* **Embedding Model:** Hugging Face `all-MiniLM-L6-v2` (Local execution, 384 dimensions).
* **LLM Inference:** Groq Cloud (`llama-3.1-8b-instant`).
* **Containerization:** Docker & Docker Compose.

## 3. Database Schema (Entity Relationship Diagram)

The system utilizes a unified database approach, storing both relational application data and high-dimensional vector embeddings in the same PostgreSQL instance.

* **USERS:** Manages staff identity (`user_id`, `staff_name`, `role`, `department`).
* **DOCUMENTS:** Stores the chunked knowledge base (`doc_id`, `category`, `version_date`, `content`, `embedding [VECTOR(384)]`).
* **QUERIES:** Logs the system's operational history (`query_id`, `user_id` [FK], `user_prompt`, `ai_answer`, `timestamp`).
* **FEEDBACK:** Captures quality assurance metrics (`feedback_id`, `query_id` [FK], `rating`, `engineers_comment`).

## 4. Development Milestones & Implemented Phases

### Phase 1: Foundation & Database Initialization

Established the core infrastructure, networking, and data models required for the application to function.

* **Dockerized Infrastructure:** Configured a `docker-compose.yml` file to spin up a specialized PostgreSQL container (`pgvector/pgvector:pg16`) alongside the FastAPI application container, connected via an internal Docker network.
* **ORM Implementation:** Designed robust SQLAlchemy models mapping directly to the ERD, defining primary keys, foreign key constraints, and one-to-many/one-to-one relationships.
* **Automated Schema Generation:** Programmed the FastAPI application lifecycle (`@app.on_event("startup")`) to automatically execute raw SQL to enable the `pgvector` extension and dynamically generate all relational tables if they do not exist on boot.

### Phase 2: Data Ingestion & Vectorization

Built the automated pipeline to transform raw, unstructured technical PDFs into machine-readable mathematical representations.

* **Document Parsing:** Implemented `PyPDFLoader` to programmatically extract text from technical support manuals (e.g., `troubleshooting_guide.pdf`).
* **Recursive Chunking:** Utilized LangChain's `RecursiveCharacterTextSplitter` to divide massive documents into optimal 1,000-character chunks with a 100-character overlap, ensuring context is not lost at the boundaries of paragraphs.
* **Local Embedding Generation:** Shifted from paid APIs to a fully local pipeline using Hugging Face's `all-MiniLM-L6-v2` model. This converts each text chunk into a 384-dimensional floating-point array.
* **Vector Storage:** Engineered the database insertion logic to store the raw text payload alongside its corresponding 384-dimensional vector representation directly into the `DOCUMENTS` table.

### Phase 3: Semantic Search & AI Generation (The RAG Pipeline)

Engineered the core intelligence of the application, connecting user inputs to backend database retrieval and LLM generation.

* **Semantic Retrieval Engine:** Built the `/ask` API endpoint. When a user submits a query, the backend converts the query into a vector using the local Hugging Face model, executes a mathematical similarity search against `pgvector`, and retrieves the most relevant document chunks.
* **LLM Orchestration:** Integrated Groq's high-speed inference API running `llama-3.1-8b-instant`. The system constructs a strict prompt template, injecting the retrieved database context and the user's question, forcing the AI to answer *only* based on the provided technical documentation.
* **State Persistence:** Configured the endpoint to extract the `AIMessage` content and log the exact user prompt, AI response, and timestamp into the `QUERIES` table for auditability.
* **Frontend Dashboard:** Developed a responsive, single-page application using Tailwind CSS. It features asynchronous JavaScript `fetch` calls, loading state animations, and renders the LLM's Markdown output.
* **Quality Assurance Loop:** Implemented a `/feedback` endpoint and UI integration allowing Senior Engineers to rate AI responses (1 to 5) directly from the interface, linking the rating back to the specific `query_id` for future system optimization.

## 5. Running the Application

Ensure the Docker daemon is running on your machine. From the project root directory, execute:

```bash
docker compose up --build -d

```

* **Frontend Interface:** `http://localhost:8000/`
* **API Documentation (Swagger UI):** `http://localhost:8000/docs`
* **Database:** Accessible via port `5432` on the Docker network.

To ingest new documents, place the PDF in the root directory, ensure `ingest.py` points to the correct filename, and run the script locally while the database container is active.

## Phase 4: Future Enhancements
1) Production Deployment: Containerize the FastAPI backend and static frontend. Deploy to a cloud environment and migrate to a managed PostgreSQL instance to handle pgvector at scale.

2) Authentication and Role-Based Access: Implement JWT or OAuth. Restrict the feedback endpoint so only authenticated users with the "Senior Engineer" role can submit ratings.

3) Automated Data Pipeline: Replace the manual ingest.py script with a webhook or cron job. This ensures new technical PDFs or wiki updates are automatically chunked and embedded without developer intervention.

4) Agentic Workflow Architecture: Upgrade the linear LangChain retrieval pipeline to a multi-agent system using LangGraph. This allows the system to route queries intelligently, trigger external APIs for real-time diagnostics, or execute multi-step reasoning before answering.

