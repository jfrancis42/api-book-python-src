from fastapi import FastAPI
from routers import v1, v2

app = FastAPI(title="Mini-GitHub API — versioned")

app.include_router(v1.router, prefix="/v1")
app.include_router(v2.router, prefix="/v2")
