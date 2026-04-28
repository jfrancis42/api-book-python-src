from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import sys; sys.path.insert(0, "..")
import database, crud
from models import IssueCreate, IssueResponse

router = APIRouter(tags=["issues"])


@router.get("/repos/{owner}/{repo}/issues", response_model=list[IssueResponse])
def list_issues(owner: str, repo: str, state: str = "open",
                db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.get_repo_issues(db, owner, repo, state=state)


@router.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse, status_code=201)
def create_issue(owner: str, repo: str, issue_in: IssueCreate,
                 db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.create_issue(
        db, owner=owner, repo=repo, author="anonymous",
        title=issue_in.title, body=issue_in.body, labels=issue_in.labels,
    )


@router.get("/repos/{owner}/{repo}/issues/{number}", response_model=IssueResponse)
def get_issue(owner: str, repo: str, number: int, db: Session = Depends(database.get_db)):
    issue = crud.get_issue(db, owner, repo, number)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found")
    return issue
