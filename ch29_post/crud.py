"""CRUD operations for Mini-GitHub (Chapter 24)."""
from sqlalchemy.orm import Session
from orm_models import User, Repo, Issue


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user(db: Session, login: str) -> User | None:
    return db.query(User).filter(User.login == login.lower()).first()


def get_users(db: Session, skip: int = 0, limit: int = 30) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, login: str, name: str | None = None,
                bio: str | None = None, email: str | None = None) -> User:
    user = User(login=login.lower(), name=name, bio=bio, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

def get_repo(db: Session, owner: str, name: str) -> Repo | None:
    return db.query(Repo).filter(
        Repo.owner == owner.lower(),
        Repo.name == name,
    ).first()


def get_user_repos(db: Session, owner: str, skip: int = 0, limit: int = 30) -> list[Repo]:
    return (db.query(Repo)
            .filter(Repo.owner == owner.lower())
            .order_by(Repo.updated_at.desc())
            .offset(skip).limit(limit).all())


def create_repo(db: Session, owner: str, name: str, description: str | None = None,
                language: str | None = None, private: bool = False) -> Repo:
    repo = Repo(owner=owner.lower(), name=name, description=description,
                language=language, private=private)
    db.add(repo)
    # Update the owner's public_repos count
    user = get_user(db, owner)
    if user and not private:
        user.public_repos += 1
    db.commit()
    db.refresh(repo)
    return repo


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

def get_next_issue_number(db: Session, owner: str, repo: str) -> int:
    last = (db.query(Issue)
            .filter(Issue.owner == owner.lower(), Issue.repo == repo)
            .order_by(Issue.number.desc())
            .first())
    return (last.number + 1) if last else 1


def get_issue(db: Session, owner: str, repo: str, number: int) -> Issue | None:
    return db.query(Issue).filter(
        Issue.owner == owner.lower(),
        Issue.repo == repo,
        Issue.number == number,
    ).first()


def get_repo_issues(db: Session, owner: str, repo: str, state: str = "open",
                    skip: int = 0, limit: int = 30) -> list[Issue]:
    q = db.query(Issue).filter(Issue.owner == owner.lower(), Issue.repo == repo)
    if state != "all":
        q = q.filter(Issue.state == state)
    return q.order_by(Issue.created_at.desc()).offset(skip).limit(limit).all()


def create_issue(db: Session, owner: str, repo: str, author: str,
                 title: str, body: str = "", labels: list[str] | None = None) -> Issue:
    number = get_next_issue_number(db, owner, repo)
    issue = Issue(
        number=number, title=title, body=body, owner=owner.lower(),
        repo=repo, author=author, labels_str=",".join(labels or []),
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue
