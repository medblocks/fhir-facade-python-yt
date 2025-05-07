# SQLAlchemy engine & session helpers 
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5440/postgres"
)

logger.info(f"Connecting to database at: {DATABASE_URL}")

# Create async engine
try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,  # Set to False in production
        future=True,
        poolclass=NullPool  # Disable connection pooling for development
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Error creating database engine: {e}")
    raise

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()

# Dependency to get DB session
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close() 