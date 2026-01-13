from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlmodel import Session
from typing import List
from uuid import UUID
from app.database import get_session
from app.models import User, Repository, RepositoryStatus
from app.schemas import RepoCreate, RepoRead, QuestionRequest, AnswerResponse
from app.api.deps import get_current_user
from app.services.ingestion import ingest_repository_task
from app.services.qa import ask_question

router = APIRouter()

@router.post("/ingest", response_model=RepoRead, status_code=202)
def ingest_repo(
    repo_in: RepoCreate, 
    background_tasks: BackgroundTasks, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    # Check if already exists for user
    existing_repo = session.query(Repository).filter(Repository.url == repo_in.github_url, Repository.owner_id == current_user.id).first()
    if existing_repo:
        raise HTTPException(status_code=400, detail="Repository already exists for this user")
    
    # Extract name from URL (simple logic)
    repo_name = repo_in.github_url.rstrip("/").split("/")[-1]
    
    new_repo = Repository(
        owner_id=current_user.id,
        name=repo_name,
        url=repo_in.github_url,
        status=RepositoryStatus.PENDING
    )
    session.add(new_repo)
    session.commit()
    session.refresh(new_repo)
    
    background_tasks.add_task(ingest_repository_task, new_repo.id)
    
    return new_repo

@router.get("/", response_model=List[RepoRead])
def list_repos(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return current_user.repositories

@router.post("/{repo_id}/chat", response_model=AnswerResponse)
def chat_repo(
    repo_id: UUID, 
    question_in: QuestionRequest, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this repository")
    
    if repo.status != RepositoryStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Repository not ready. Status: {repo.status}")
        
    result = ask_question(repo.id, question_in.question)
    return result
