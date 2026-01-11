import git
import tempfile
import os
from pathlib import Path
from sqlmodel import Session
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from ..models import Repository, CodeChunk, RepositoryStatus
from app.core.config import settings
import logging

# Configure Logging
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

IGNORE_PATTERNS = [
    ".git", "node_modules", "__pycache__", ".env", 
    "*.pyc", "*.o", "*.so", "*.a", "*.dll", "*.exe",
    "*.jpg", "*.png", "*.gif", "*.svg", "*.ico",
    "package-lock.json", "yarn.lock", "dist", "build"
]

def is_ignored(path: Path, repo_root: Path) -> bool:
    # Basic implementation of ignore logic
    # In a real app, we might use gitignore_parser or fnmatch more robustly
    import fnmatch
    rel_path = path.relative_to(repo_root)
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(str(rel_path), pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        # Check parent directories
        for part in rel_path.parts:
             if fnmatch.fnmatch(part, pattern):
                 return True
    return False

def process_repository(repo_id: int, db_session_generator):
    """
    Background task to process the repository.
    db_session_generator: A factory/generator to get a fresh session since objects cannot be passed across threads easily if bound to a closed session.
    However, BackgroundTasks in FastAPI run in the same loop usually, but it's safer to manage session lifecycle here.
    """
    # We need a new session for the background task
    # Since we passed a generator or the session directly from Depends, 
    # but `BackgroundTasks` usually run after the response is sent, the original session might be closed.
    # The best practice is to pass the session *factory* or create a new session here. 
    # For simplicity with the current structure, we will import get_session and creating a new one.
    
    from ..database import engine
    
    with Session(engine) as db:
        repo = db.get(Repository, repo_id)
        if not repo:
            logger.error(f"Repository {repo_id} not found for ingestion.")
            return
        
        logger.info(f"Starting ingestion for repo: {repo.github_url}")
        repo.status = RepositoryStatus.INGESTING
        db.add(repo)
        db.commit()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 2. Clone repo
                logger.info(f"Cloning {repo.github_url}...")
                git.Repo.clone_from(repo.github_url, temp_dir)

                # 3. Initialize text splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500, 
                    chunk_overlap=200
                )

                root_path = Path(temp_dir)
                all_chunks = []
                all_chunk_metadata = []

                # 4. Walk directory
                for file_path in root_path.rglob("*"):
                    if file_path.is_file() and not is_ignored(file_path, root_path):
                        try:
                            # Try reading as utf-8, skip if binary
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            chunks = text_splitter.split_text(content)
                            for chunk in chunks:
                                all_chunks.append(chunk)
                                all_chunk_metadata.append({
                                    "file_path": str(file_path.relative_to(root_path)),
                                    "text": chunk
                                })
                        except UnicodeDecodeError:
                            # Binary file, skip
                            continue
                        except Exception:
                            continue

                # 5. Embed in Batches
                batch_size = 100
                for i in range(0, len(all_chunks), batch_size):
                    batch_texts = all_chunks[i:i+batch_size]
                    batch_meta = all_chunk_metadata[i:i+batch_size]

                    if not batch_texts:
                        continue

                    # Call Google Embedding API
                    response = genai.embed_content(
                        model="models/text-embedding-004",
                        content=batch_texts,
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                    
                    # The response structure might slightly vary, usually it's dict with 'embedding' key which is a list of lists
                    embeddings = response['embedding']

                    # 6. Store in DB
                    for meta, embedding in zip(batch_meta, embeddings):
                        code_chunk = CodeChunk(
                            repository_id=repo.id,
                            file_path=meta['file_path'],
                            chunk_text=meta['text'],
                            embedding=embedding
                        )
                        db.add(code_chunk)

            # 7. Mark as READY
            logger.info(f"Ingestion complete for {repo.github_url}")
            repo.status = RepositoryStatus.READY
            db.add(repo)
            db.commit()

        except Exception as e:
            # 8. Handle Failure
            logger.error(f"Ingestion failed for {repo.github_url}: {e}")
            repo.status = RepositoryStatus.FAILED
            repo.error_message = str(e)
            db.add(repo)
            db.commit()
