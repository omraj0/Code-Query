from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import auth, repos

app = FastAPI(title="Code-Query", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event
@app.on_event("startup")
def on_startup():
    init_db()

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(repos.router, prefix="/repos", tags=["Repositories"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Code-Query API"}