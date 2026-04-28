"""ORM models extended with readme and avatar_path (Chapter 35)."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login: Mapped[str] = mapped_column(String(39), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_repos: Mapped[int] = mapped_column(Integer, default=0)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    repos: Mapped[list["Repo"]] = relationship("Repo", back_populates="user")


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner: Mapped[str] = mapped_column(String(39), ForeignKey("users.login"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(350), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    readme: Mapped[str | None] = mapped_column(Text, nullable=True)
    stargazers_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship("User", back_populates="repos")

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(10), default="open")
    owner: Mapped[str] = mapped_column(String(39), nullable=False)
    repo: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(39), nullable=False)
    labels_str: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    @property
    def labels(self) -> list[str]:
        return [l for l in self.labels_str.split(",") if l] if self.labels_str else []
