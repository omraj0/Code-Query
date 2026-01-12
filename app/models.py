from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, Column
from pgvector.sqlalchemy import Vector
from sqlalchemy import Text

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    
    repositories: List["Repository"] = Relationship(back_populates="owner")

class Repository(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")
    name: str
    url: str
    status: str = Field(default="Pending") # Pending, Processing, Completed, Failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    owner: User = Relationship(back_populates="repositories")
    chunks: List["CodeChunk"] = Relationship(back_populates="repository")

class CodeChunk(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    repo_id: UUID = Field(foreign_key="repository.id")
    file_path: str
    chunk_index: int
    content: str = Field(sa_column=Column(Text))
    embedding: List[float] = Field(sa_column=Column(Vector(768)))
    
    repository: Repository = Relationship(back_populates="chunks")
