from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.database import get_session, engine
from app.models import User, Repository, CodeChunk, RepositoryStatus, SQLModel
from app.auth import get_current_user, create_access_token, get_password_hash, verify_password
from app.core.config import settings
from app.services.ingestion import process_repository
import google.generativeai as genai
from datetime import timedelta
from typing import List
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create tables on startup (simplest way, for production assume migrations)
# Warning: pgvector extension must exist.
SQLModel.metadata.create_all(engine)

app = FastAPI(title="Code-Query API")

logger.info("Application starting up...")

# --- Pydantic Models for Requests ---
class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class RepoRequest(BaseModel):
    repo_url: str

class AskRequest(BaseModel):
    repo_id: int
    question: str

# --- Auth Endpoints ---
@app.post("/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_session)):
    db_user = db.exec(select(User).where(User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Ingestion Endpoint ---
@app.post("/api/ingest_repo")
def ingest_repo(
    request: RepoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # 1. Create the repository entry
    new_repo = Repository(
        github_url=request.repo_url, 
        user_id=current_user.id,
        status=RepositoryStatus.PENDING
    )
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)

    # 2. Add the heavy-lifting to the background
    background_tasks.add_task(process_repository, new_repo.id, get_session)
    
    # 3. Return immediately
    return new_repo

# --- Query Endpoint (The RAG Pipeline) ---
@app.post("/api/ask")
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    repo_id = request.repo_id
    question = request.question
    
    # 1. Verify user owns this repo
    repo = db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if repo.status != RepositoryStatus.READY:
        raise HTTPException(status_code=400, detail="Repository is not ready for querying")

    # 2. Retrieve (R)
    # 2a. Embed the user's question
    # Note: Configure API Key in main or ensure it is loaded. 
    # It is loaded in ingestion service but good to ensure availability here.
    import os
    if not os.getenv("GEMINI_API_KEY"):
         raise HTTPException(status_code=500, detail="Gemini API Key not configured")

    query_embedding_response = genai.embed_content(
        model="models/text-embedding-004",
        content=question,
        task_type="RETRIEVAL_QUERY"
    )
    query_embedding = query_embedding_response['embedding']

    # 2b. Perform semantic search (pgvector magic)
    # We use the cosine distance operator (<=>)
    # In SQLModel/SQLAlchemy, we can use the `cosine_distance` method of the vector column
    retrieved_chunks = db.exec(
        select(CodeChunk)
        .where(CodeChunk.repository_id == repo_id)
        .order_by(CodeChunk.embedding.cosine_distance(query_embedding))
        .limit(5)
    ).all()

    # 3. Augment (A)
    context_str = ""
    source_files = set()
    for chunk in retrieved_chunks:
        context_str += f"--- Context from {chunk.file_path} ---\n"
        context_str += chunk.chunk_text
        context_str += "\n----------------------------------------\n"
        source_files.add(chunk.file_path)

    prompt_template = f"""
    You are an expert pair-programmer AI. A developer is asking a question about their codebase.
    Here is the developer's question:
    {question}

    I have retrieved the most relevant code snippets from the repository to help you answer. Here they are:
    {context_str}

    Please answer the developer's question based *only* on the context provided. 
    If the context is not sufficient to answer, state that clearly.
    Cite the source files you used in your answer.
    Answer:
    """

    # 4. Generate (G)
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt_template)

    return {
        "answer": response.text,
        "sources": list(source_files)
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to Code-Query API"}
