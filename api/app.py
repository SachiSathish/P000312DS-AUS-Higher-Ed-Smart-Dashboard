
import os

from fastapi import FastAPI
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# Database configuration
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL = (
    f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@db:{DB_PORT}/{DB_NAME}"
)


# FastAPI application
app = FastAPI(
    title="AUS Higher Ed Smart Dashboard API",
    description="Backend API for the AUS Higher Ed Smart Dashboard project",
    version="0.1.0",
)

engine = create_engine(DATABASE_URL)


# ------------------------------------------------------------
# Basic API endpoints
# ------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "AUS Higher Ed Smart Dashboard API"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok"
    }


@app.get("/api/info")
async def api_info():
    return {
        "project": "AUS Higher Ed Smart Dashboard",
        "api_version": "0.1.0",
        "status": "development",
        "database": "PostgreSQL"
    }


# ------------------------------------------------------------
# Sample statistical data endpoint
# This does not require the final database schema.
# ------------------------------------------------------------

@app.get("/api/sample-observations")
async def sample_observations():
    return {
        "observations": [
            {
                "metric": "student_headcount",
                "period": "2024",
                "value": 13906,
                "dimensions": {
                    "institution": "Charles Sturt University",
                    "state": "New South Wales",
                    "student_cohort": "Commencing Students"
                }
            },
            {
                "metric": "student_headcount",
                "period": "2024",
                "value": 35003,
                "dimensions": {
                    "institution": "Charles Sturt University",
                    "state": "New South Wales",
                    "student_cohort": "All Students"
                }
            }
        ]
    }


# ------------------------------------------------------------
# Existing database test endpoint
# ------------------------------------------------------------

@app.get("/db_test")
async def db_test():
    with Session(engine) as session:
        res = [
            str(row)
            for row in session.execute(
                sqlalchemy.text("SELECT version();")
            ).all()
        ]

        return {
            "message": res
        }


# Existing test endpoint
@app.get("/testsss")
async def test_route():
    return {
        "message": "Hello World"
    }