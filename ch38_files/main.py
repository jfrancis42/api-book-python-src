"""Chapter 35: File upload and download endpoints.

Install: pip install python-multipart aiofiles
Run:     uvicorn main:app --reload

Endpoints:
  PUT  /users/{username}/avatar         upload avatar image
  GET  /users/{username}/avatar         download avatar image
  PUT  /repos/{owner}/{repo}/readme     upload README.md content
  GET  /repos/{owner}/{repo}/readme     download README as text/plain
"""
import io
import os
import sys
import shutil
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Depends, Request, Response, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import orm_models, database, crud
from models import UserCreate, UserResponse, RepoCreate, RepoResponse

orm_models.Base.metadata.create_all(bind=database.engine)

AVATAR_DIR = "/tmp/mini-github-avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

app = FastAPI(title="Mini-GitHub", version="1.5.0")


# ---------------------------------------------------------------------------
# Standard endpoints (abbreviated)
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(user_in: UserCreate, db: Session = Depends(database.get_db)):
    if crud.get_user(db, user_in.login):
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    return crud.create_user(db, **user_in.model_dump())


@app.get("/users/{username}", response_model=UserResponse, name="get_user", tags=["users"])
def get_user(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.post("/users/{username}/repos", response_model=RepoResponse, status_code=201, tags=["repos"])
def create_repo(username: str, repo_in: RepoCreate, db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=409,
                            detail=f"Repository '{username}/{repo_in.name}' already exists")
    return crud.create_repo(db, owner=username, **repo_in.model_dump())


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse, name="get_repo", tags=["repos"])
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


# ---------------------------------------------------------------------------
# Avatar upload / download
# ---------------------------------------------------------------------------

@app.put("/users/{username}/avatar", tags=["users"])
async def upload_avatar(
    username: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="File must be an image")

    # Verify magic bytes (JPEG or PNG)
    header = await file.read(8)
    await file.seek(0)
    is_jpeg = header[:2] == b"\xff\xd8"
    is_png = header[:4] == b"\x89PNG"
    if not (is_jpeg or is_png):
        raise HTTPException(status_code=422,
                            detail="File must be a JPEG or PNG image")

    dest = os.path.join(AVATAR_DIR, username)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Store path on user record
    user.avatar_path = dest
    db.commit()

    return {"message": "Avatar uploaded", "filename": file.filename}


@app.get("/users/{username}/avatar", tags=["users"])
def get_avatar(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user or not user.avatar_path:
        raise HTTPException(status_code=404, detail="No avatar uploaded")
    if not os.path.exists(user.avatar_path):
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(user.avatar_path, media_type="image/png")


# ---------------------------------------------------------------------------
# README upload / download
# ---------------------------------------------------------------------------

@app.put("/repos/{owner}/{repo}/readme", tags=["repos"])
async def upload_readme(
    owner: str, repo: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    if file.filename and not file.filename.endswith(".md"):
        raise HTTPException(status_code=422, detail="File must be a Markdown (.md) file")
    content = await file.read()
    r.readme = content.decode("utf-8", errors="replace")
    db.commit()
    return {"message": "README uploaded", "size": len(content)}


@app.get("/repos/{owner}/{repo}/readme", tags=["repos"])
def get_readme(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r or not r.readme:
        raise HTTPException(status_code=404, detail="README not found")
    content = r.readme.encode()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Length": str(len(content))},
    )
