from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings
from sqlalchemy import text

# Assuming DATABASE_URL is set in .env or config
# Note: Helper to ensure async pg driver if needed, but standard psycopg2 is fine for now
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    # Fallback/Placeholder if env var not set, though it should be.
    # We use sqlite for local testing if no postgres provided, but pgvector needs postgres
    # So we prefer to fail or warn if not postgres.
    pass

engine = create_engine(DATABASE_URL if DATABASE_URL else "sqlite:///./test.db") 

def init_db():
    # Only useful if we wanted to auto-create tables, 
    # but for pgvector we usually need to ensure extension exists first.
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
