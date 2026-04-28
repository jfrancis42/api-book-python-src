"""CRUD with count functions for pagination (Chapter 31)."""
from sqlalchemy import func
from sqlalchemy.orm import Session
from orm_models import User, Repo, Issue


def get_user(db, login): return db.query(User).filter(User.login == login.lower()).first()
def get_users(db, skip=0, limit=30): return db.query(User).offset(skip).limit(limit).all()


def create_user(db, login, name=None, bio=None, email=None):
    u = User(login=login.lower(), name=name, bio=bio, email=email)
    db.add(u); db.commit(); db.refresh(u); return u


def update_user(db, login, updates):
    user = get_user(db, login)
    if not user: return None
    for k, v in updates.items(): setattr(user, k, v)
    db.commit(); db.refresh(user); return user


def get_repo(db, owner, name):
    return db.query(Repo).filter(Repo.owner == owner.lower(), Repo.name == name).first()


def get_user_repos(db, owner, skip=0, limit=30):
    return (db.query(Repo).filter(Repo.owner == owner.lower())
            .order_by(Repo.updated_at.desc()).offset(skip).limit(limit).all())


def count_user_repos(db, owner: str) -> int:
    return db.query(func.count(Repo.id)).filter(Repo.owner == owner.lower()).scalar()


def create_repo(db, owner, name, description=None, language=None, private=False):
    repo = Repo(owner=owner.lower(), name=name, description=description,
                language=language, private=private)
    db.add(repo)
    user = get_user(db, owner)
    if user and not private:
        user.public_repos += 1
    db.commit(); db.refresh(repo); return repo


def update_repo(db, owner, name, updates):
    repo = get_repo(db, owner, name)
    if not repo: return None
    for k, v in updates.items(): setattr(repo, k, v)
    db.commit(); db.refresh(repo); return repo


def delete_repo(db, owner, name):
    repo = get_repo(db, owner, name)
    if not repo: return False
    user = get_user(db, owner)
    if user and not repo.private:
        user.public_repos = max(0, user.public_repos - 1)
    db.delete(repo); db.commit(); return True


def get_next_issue_number(db, owner, repo):
    last = (db.query(Issue).filter(Issue.owner == owner.lower(), Issue.repo == repo)
            .order_by(Issue.number.desc()).first())
    return (last.number + 1) if last else 1


def get_issue(db, owner, repo, number):
    return db.query(Issue).filter(Issue.owner == owner.lower(),
                                  Issue.repo == repo, Issue.number == number).first()


def get_repo_issues(db, owner, repo, state="open", skip=0, limit=30):
    q = db.query(Issue).filter(Issue.owner == owner.lower(), Issue.repo == repo)
    if state != "all":
        q = q.filter(Issue.state == state)
    return q.order_by(Issue.created_at.desc()).offset(skip).limit(limit).all()


def count_repo_issues(db, owner: str, repo: str, state: str = "open") -> int:
    q = db.query(func.count(Issue.id)).filter(Issue.owner == owner.lower(), Issue.repo == repo)
    if state != "all":
        q = q.filter(Issue.state == state)
    return q.scalar()


def create_issue(db, owner, repo, author, title, body="", labels=None):
    number = get_next_issue_number(db, owner, repo)
    issue = Issue(number=number, title=title, body=body, owner=owner.lower(),
                  repo=repo, author=author, labels_str=",".join(labels or []))
    db.add(issue); db.commit(); db.refresh(issue); return issue


def update_issue(db, owner, repo, number, updates):
    issue = get_issue(db, owner, repo, number)
    if not issue: return None
    if "labels" in updates:
        updates["labels_str"] = ",".join(updates.pop("labels"))
    for k, v in updates.items(): setattr(issue, k, v)
    db.commit(); db.refresh(issue); return issue
