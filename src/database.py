from typing import AsyncGenerator
from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import String, Boolean, Column, Integer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeMeta, declarative_base, sessionmaker, Mapped, mapped_column

from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME


DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
Base: DeclarativeMeta = declarative_base()


class User(SQLAlchemyBaseUserTable[int], Base):
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
