# Code-Query

Code-Query is a RAG-based (Retrieval-Augmented Generation) application that allows you to "chat" with your codebase. It ingests GitHub repositories, chunks the code, embeds it using Google's Gemini models, and stores the vectors in PostgreSQL (pgvector) for semantic search.

## 🚀 Features

*   **FastAPI Backend**: High-performance async API.
*   **Google Gemini AI**: Utilizes `text-embedding-004` for embeddings and `gemini-1.5-pro` for answer generation.
*   **Vector Search**: PostgreSQL with `pgvector` for efficient similarity search.
*   **Background Ingestion**: Asynchronous processing of repositories using `BackgroundTasks` to handle large codebases without timeouts.
*   **Smart Chunking**: Uses LangChain's `RecursiveCharacterTextSplitter` optimized for code.
*   **Secure Auth**: JWT-based authentication.

## 🛠️ Tech Stack

*   **Framework**: FastAPI
*   **Database**: PostgreSQL + pgvector
*   **ORM**: SQLModel (SQLAlchemy)
*   **AI/LLM**: Google Generative AI (Gemini)
*   **Deployment**: Render

## 💻 Local Setup

### Prerequisites
1.  **Python 3.10+**
2.  **PostgreSQL** installed locally.
3.  **pgvector extension**:
    *   **Recommended (Docker)**: Run `docker run -d --name codequery-db -p 5432:5432 -e POSTGRES_PASSWORD=password ankane/pgvector`
    *   **Native**: You must enable the extension on your database:
        ```sql
        CREATE EXTENSION IF NOT EXISTS vector;
        ```
4.  **Google Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/).

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd Code-Query
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    DATABASE_URL=postgresql://postgres:password@localhost:5432/codequery
    GEMINI_API_KEY=your_gemini_api_key_here
    JWT_SECRET_KEY=your_super_secret_key
    ```

5.  **Run the Application**:
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.
    Access the interactive docs at `http://127.0.0.1:8000/docs`.

## ☁️ Deployment (Render)

This project is configured for easy deployment on [Render](https://render.com/).

1.  **New Web Service**: Connect your GitHub repository.
2.  **Build Command**: `pip install -r requirements.txt`
3.  **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
4.  **Environment Variables**: Set `DATABASE_URL`, `GEMINI_API_KEY`, and `JWT_SECRET_KEY` in the Render dashboard.
5.  **Database**:
    *   Create a PostgreSQL database on Render.
    *   **Crucial Step**: Connect to the database (via Render's internal shell or external connection) and run:
        ```sql
        CREATE EXTENSION IF NOT EXISTS vector;
        ```

## 🔌 API Endpoints

### Authentication
*   `POST /auth/register`: Register a new user.
*   `POST /auth/token`: Login and get a JWT access token.

### Core
*   `POST /api/ingest_repo`: Submit a GitHub URL for ingestion (runs in background).
    *   Body: `{"repo_url": "https://github.com/username/repo"}`
*   `POST /api/ask`: Ask a question about an ingested repository.
    *   Body: `{"repo_id": 1, "question": "How does the auth logic work?"}`