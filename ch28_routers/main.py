"""Chapter 25: Router-organized Mini-GitHub server."""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI
import orm_models
import database
from routers import users, repos, issues

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="0.5.0")

app.include_router(users.router)
app.include_router(repos.router)
app.include_router(issues.router)
