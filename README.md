# Code-Query

**Code-Query** is a Retrieval-Augmented Generation (RAG) based application that allows developers to "chat" with their codebase. It ingests GitHub repositories, processes the source code into semantic vector embeddings, and uses Google's Gemini AI to answer natural language questions about the code.

## 🚀 Features

*   **Repository Ingestion**: Asynchronously clones, filters, chunks, and embeds public GitHub repositories.
*   **Semantic Search**: Uses `pgvector` (PostgreSQL) to find the most relevant code snippets for a user's question.
*   **AI-Powered Q&A**: Uses Google Gemini 1.5 Pro to generate context-aware answers based on the retrieved code.
*   **Authentication**: Secure JWT-based signup and login system.
*   **Dashboard Ready**: API endpoints designed to support a frontend dashboard for managing repos and chats.

## 🛠️ Tech Stack

*   **Language**: Python 3.12+
*   **Framework**: FastAPI (High-performance, async web framework)
*   **Database**: PostgreSQL 14+ with `pgvector` extension
*   **ORM**: SQLModel (SQLAlchemy + Pydantic)
*   **AI Models**:
    *   **Embeddings**: `models/text-embedding-004` (via Google AI)
    *   **LLM**: `gemini-2.5-flash` (via Google AI)
*   **Services**:
    *   `GitPython`: For cloning repositories.
    *   `LangChain`: For text splitting/chunking.

## 🏗️ Architecture

### 1. Database Schema
*   **User**: Stores authentication details.
*   **Repository**: Tracks the lifecycle of an ingested repo (`Pending` -> `Processing` -> `Completed` / `Failed`).
*   **CodeChunk**: Valid source code files are split into chunks (approx 2000 chars). Each chunk is stored with its vector embedding (768 dimensions).

### 2. Ingestion Pipeline
When a user submits a repo URL:
1.  **Clone**: The repo is cloned to a temporary directory.
2.  **Filter**: Non-code files (images, binaries, `.git`) are ignored.
3.  **Chunk**: Source files are split into overlapping chunks to preserve context.
4.  **Embed**: Each chunk is passed to the Gemini Embedding API.
5.  **Store**: Text and vectors are saved to PostgreSQL.

### 3. Q&A Pipeline
When a user asks a question:
1.  **Embed Query**: The question is converted to a vector.
2.  **Search**: `pgvector` calculates Cosine Similarity to find the top 5 most relevant code chunks.
3.  **Generate**: A prompt is constructed with the User Query + Retrieved Code Context.
4.  **Trace**: The LLM generates an answer, citing the source files used.

## 📦 Installation & Setup

### Prerequisites
*   Python 3.10+
*   PostgreSQL with `pgvector` extension installed (`brew install pgvector` on Mac).
*   Google AI Studio API Key.

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/code-query.git
    cd code-query
    ```

2.  **Install Dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configuration**
    Create a `.env` file:
    ```bash
    cp .env.example .env
    ```
    Update the values:
    ```ini
    DATABASE_URL=postgresql://user:password@localhost:5432/codequery
    GEMINI_API_KEY=your_google_api_key
    ```
    *Note: Ensure your `DATABASE_URL` uses `postgresql://` protocol.*

4.  **Run the Server**
    ```bash
    python app/main.py
    # OR
    uvicorn app.main:app --reload
    ```

5.  **Documentation**
    Visit `http://localhost:8000/docs` for the interactive Swagger UI.

## 🧪 Usage

1.  **Authorize**: Create an account via `/auth/signup` and login via `/auth/login` to get a Bearer token.
2.  **Ingest**: POST to `/repos/ingest` with `{"github_url": "..."}`.
3.  **Chat**: POST to `/repos/{repo_id}/chat` to ask questions.

## 📂 Project Structure

```
app/
├── api/            # API Route Handlers
│   ├── auth.py     # Login/Signup
│   ├── repos.py    # Repo Management & Chat
│   └── deps.py     # Dependencies (CurrentUser)
├── core/           # Config & Security
├── services/       # Business Logic
│   ├── gemini.py   # AI Integration
│   ├── ingestion.py# Background Processing
│   └── qa.py       # RAG Logic
├── database.py     # DB Engine & Session
├── models.py       # SQLModel Tables
└── main.py         # Entry Point
```