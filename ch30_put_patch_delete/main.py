"""Chapter 28: PATCH, PUT, DELETE endpoints."""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI
import orm_models, database
from routers import users, repos, issues

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="0.8.0")
app.include_router(users.router)
app.include_router(repos.router)
app.include_router(issues.router)
