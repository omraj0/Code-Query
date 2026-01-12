from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class UserCreate(BaseModel):
    email: str
    password: str

class UserRead(BaseModel):
    id: UUID
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str

class RepoCreate(BaseModel):
    github_url: str

class RepoRead(BaseModel):
    id: UUID
    name: str
    url: str
    status: str

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str
    sources: List[str]
