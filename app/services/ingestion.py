import os
import shutil
import stat
import tempfile
import uuid
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session, select
from app.database import engine
from app.models import Repository, CodeChunk, RepositoryStatus
from app.services.gemini import get_embedding
import logging

def ingest_repository_task(repo_id: uuid.UUID):
    with Session(engine) as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            return
        
        repo.status = RepositoryStatus.PROCESSING
        session.add(repo)
        session.commit()

        logger = logging.getLogger(__name__)

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Clone
            logger.info(f"Cloning {repo.url}...")
            Repo.clone_from(repo.url, temp_dir)

            # 2. Process Files
            documents = []
            for root, dirs, files in os.walk(temp_dir):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'env', 'venv']]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.html', '.css', '.md', '.java', '.cpp', '.h', '.cs', '.go', '.rs', '.php', '.rb')):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, temp_dir)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                documents.append({"path": rel_path, "content": content})
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")

            # 3. Chunk
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                separators=["\n\n", "\n", " ", ""]
            )
            
            chunks_to_save = []
            for doc in documents:
                chunks = text_splitter.split_text(doc['content'])
                for i, chunk_text in enumerate(chunks):
                    # 4. Embed
                    try:
                        embedding = get_embedding(chunk_text)
                        
                        db_chunk = CodeChunk(
                            repo_id=repo.id,
                            file_path=doc['path'],
                            chunk_index=i,
                            content=chunk_text,
                            embedding=embedding
                        )
                        chunks_to_save.append(db_chunk)
                    except Exception as e:
                        print(f"Error embedding chunk {doc['path']}#{i}: {e}")
            
            # 5. Save
            session.add_all(chunks_to_save)
            repo.status = RepositoryStatus.COMPLETED
            session.add(repo)
            session.commit()
            logger.info(f"Ingestion completed for {repo.url}")

        except Exception as e:
            repo.status = RepositoryStatus.FAILED
            repo.error_message = str(e) # Assuming error_message field exists, if not add it or skip
            session.add(repo)
            session.commit()
            logger.error(f"Ingestion failed: {e}")
            logger.error(f"Ingestion failed: {e}")
        finally:
            if os.path.exists(temp_dir):
                def on_rm_error(func, path, exc_info):
                    # path contains the path of the file that couldn't be removed
                    # let's just assume it's read-only and unlink it.
                    os.chmod(path, stat.S_IWRITE)
                    os.unlink(path)
                shutil.rmtree(temp_dir, onerror=on_rm_error)