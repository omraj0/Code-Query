import enum
from sqlmodel import Field, SQLModel, Relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from typing import Optional, List

class RepositoryStatus(str, enum.Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    READY = "READY"
    FAILED = "FAILED"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    repositories: List["Repository"] = Relationship(back_populates="user")

class Repository(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    github_url: str
    status: RepositoryStatus = Field(default=RepositoryStatus.PENDING)
    error_message: Optional[str] = None

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="repositories")

    code_chunks: List["CodeChunk"] = Relationship(back_populates="repository")

class CodeChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str = Field(index=True)
    chunk_text: str
    # Define the vector dimension. Google's text-embedding-004 is 768
    embedding: List[float] = Field(sa_column=Column(Vector(768)))

    repository_id: int = Field(foreign_key="repository.id")
    repository: Repository = Relationship(back_populates="code_chunks")
