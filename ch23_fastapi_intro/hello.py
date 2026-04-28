"""Chapter 21: minimal FastAPI application.

Run:
    uvicorn hello:app --reload

Then visit:
    http://localhost:8000/
    http://localhost:8000/zen
    http://localhost:8000/docs      (interactive docs)
    http://localhost:8000/openapi.json
"""
from fastapi import FastAPI

app = FastAPI(title="Mini-GitHub", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Mini-GitHub API"}


@app.get("/zen")
def zen():
    return {"message": "Keep it logically awesome."}
