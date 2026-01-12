import google.genai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_embedding(text: str) -> list[float]:
    """Generates an embedding for the given text using text-embedding-004."""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
        title="Code Chunk" # Optional, helps with retrieval
    )
    return result['embedding']

def get_query_embedding(text: str) -> list[float]:
    """Generates an embedding for the query text."""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

def generate_answer(prompt: str) -> str:
    """Generates an answer using Gemini 1.5 Pro."""
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)
    return response.text