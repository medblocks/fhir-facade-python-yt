# FastAPI entry-point (Uvicorn target) 
from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
import logging

from .resources import patient, observation
from .db import engine, Base # Import Base if you want to create tables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create tables if it doesn't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        yield
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

app = FastAPI(
    title="FHIR Facade",
    description="A FastAPI application providing a FHIR interface over PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(patient.router, prefix="/fhir", tags=["Patient"])
app.include_router(observation.router, prefix="/fhir", tags=["Observation"])

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the FHIR Facade API. See /docs for API documentation."}

# Add other middleware, exception handlers, etc. as needed 