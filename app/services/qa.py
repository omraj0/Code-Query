from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy import text
from app.database import engine
from app.models import CodeChunk
from app.services.gemini import get_query_embedding, generate_answer

def ask_question(repo_id: UUID, question: str) -> dict:
    with Session(engine) as session:
        # 1. Embed Question
        query_embedding = get_query_embedding(question)
        
        # 2. Vector Search (Cosine Similarity)
        # Using pgvector's cosine distance operator <=>
        # We want the *smallest* distance, so we order by embedding <=> query_embedding
        stmt = select(CodeChunk).where(CodeChunk.repo_id == repo_id).order_by(CodeChunk.embedding.cosine_distance(query_embedding)).limit(5)
        results = session.exec(stmt).all()
        
        if not results:
            return {"answer": "No relevant code found in the repository.", "sources": []}

        # 3. Construct Prompt
        context_parts = []
        sources = []
        for chunk in results:
            context_parts.append(f"File: {chunk.file_path}\nCode:\n{chunk.content}\n")
            if chunk.file_path not in sources:
                sources.append(chunk.file_path)
        
        context_str = "\n---\n".join(context_parts)
        
        prompt = f"""You are an expert developer assistant. Answer the user's question based strictly on the code context provided below.
        Context:
        {context_str}
        Question: {question}
        Answer:
        """

        # 4. Generate Answer
        answer = generate_answer(prompt)
        
        return {
            "answer": answer,
            "sources": sources
        }