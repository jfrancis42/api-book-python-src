"""Chapter 27: POST — 201 Created and Location header.

Run: uvicorn main:app --reload
"""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI
import orm_models
import database
from routers import users, repos, issues

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="0.7.0")

app.include_router(users.router)
app.include_router(repos.router)
app.include_router(issues.router)
