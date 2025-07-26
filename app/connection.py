from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from app.models.models import Base
from app.logger import Logger
from app.handler import custom_db_connection_handler, connection_handler
import time
import asyncio


@dataclass
class Connection:

    database_type: str
    db_username: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str
    logger: Logger

    def __post_init__(self):
        self.engine = None
        self.session_maker = None
        self.session = None

    @connection_handler
    async def connect(self):
        print("connect denedi")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @custom_db_connection_handler
    async def get_session(self) -> AsyncSession:
        return self.session()

    @custom_db_connection_handler
    async def create_engine(self):
        self.database_url = f"{self.database_type}+asyncpg://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_async_engine(self.database_url, echo=False)

    @custom_db_connection_handler
    async def get_engine(self) -> AsyncEngine:
        return self.engine

    @custom_db_connection_handler
    async def create_session(self):
        self.session_maker = async_sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session = self.session_maker()

    @custom_db_connection_handler
    async def close_session(self):
        await self.session.close()



if __name__ == "__main__":
    from app.logger import Logger
    from app.connection import Connection

    logger_dict = {
        "filepath": "./logs/database.log",
        "rotation": "50MB"
    }

    logger = Logger(**logger_dict)
    logger.debug("############ DATABASE CONNECTION CONFIGURATIONS ############")
    logger.debug(logger_dict)

    parameter_dict = {
        "database_type": "postgresql",
        "db_username": "postgres",
        "db_password": "admin",
        "db_host": "localhost",
        "db_port": "5432",
        "db_name": "workplace"
    }
    connection = Connection(**parameter_dict, logger= logger)

    print(connection)

