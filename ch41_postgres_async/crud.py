"""Async CRUD operations using AsyncSession (Chapter 37)."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from orm_models import User, Repo, Issue


async def get_user(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).where(User.login == login.lower()))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, login: str, name: str | None = None,
                      bio: str | None = None, email: str | None = None) -> User:
    user = User(login=login.lower(), name=name, bio=bio, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_repos(db: AsyncSession, owner: str,
                         skip: int = 0, limit: int = 30) -> list[Repo]:
    result = await db.execute(
        select(Repo)
        .where(Repo.owner == owner.lower())
        .order_by(Repo.updated_at.desc())
        .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def count_user_repos(db: AsyncSession, owner: str) -> int:
    result = await db.execute(
        select(func.count(Repo.id)).where(Repo.owner == owner.lower())
    )
    return result.scalar()


async def get_repo(db: AsyncSession, owner: str, name: str) -> Repo | None:
    result = await db.execute(
        select(Repo).where(Repo.owner == owner.lower(), Repo.name == name)
    )
    return result.scalar_one_or_none()


async def create_repo(db: AsyncSession, owner: str, name: str,
                      description: str | None = None, language: str | None = None,
                      private: bool = False) -> Repo:
    repo = Repo(owner=owner.lower(), name=name, description=description,
                language=language, private=private)
    db.add(repo)
    user = await get_user(db, owner)
    if user and not private:
        user.public_repos += 1
    await db.commit()
    await db.refresh(repo)
    return repo


async def get_repo_issues(db: AsyncSession, owner: str, repo: str,
                          state: str = "open", skip: int = 0, limit: int = 30) -> list[Issue]:
    q = select(Issue).where(Issue.owner == owner.lower(), Issue.repo == repo)
    if state != "all":
        q = q.where(Issue.state == state)
    result = await db.execute(q.order_by(Issue.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_issue(db: AsyncSession, owner: str, repo: str, author: str,
                       title: str, body: str = "", labels: list[str] | None = None) -> Issue:
    result = await db.execute(
        select(Issue).where(Issue.owner == owner.lower(), Issue.repo == repo)
        .order_by(Issue.number.desc()).limit(1)
    )
    last = result.scalar_one_or_none()
    number = (last.number + 1) if last else 1

    issue = Issue(number=number, title=title, body=body, owner=owner.lower(),
                  repo=repo, author=author, labels_str=",".join(labels or []))
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue
