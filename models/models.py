from datetime import datetime, timezone
from typing import List

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now)

    user_words: Mapped[List["UserWord"]] = relationship(back_populates="user")


class DictionaryWord(Base):
    """Global dictionary available to everyone"""

    __tablename__ = "dictionary_words"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String, index=True, unique=True)
    translation: Mapped[str] = mapped_column(String)
    definition: Mapped[str] = mapped_column(Text, nullable=True)
    example_sentence: Mapped[str] = mapped_column(Text, nullable=True)


class UserWord(Base):
    """Words added/tracked by specific users for spaced repetition"""

    __tablename__ = "user_words"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    word: Mapped[str] = mapped_column(String, index=True)
    translation: Mapped[str] = mapped_column(String)

    last_reviewed: Mapped[datetime] = mapped_column(default=get_utc_now)
    next_review: Mapped[datetime] = mapped_column(default=get_utc_now)
    repetition_level: Mapped[int] = mapped_column(default=0)

    user: Mapped["User"] = relationship(back_populates="user_words")
