import os
from fastapi import FastAPI
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@db:{DB_PORT}/{DB_NAME}"

app = FastAPI()
engine = create_engine(DATABASE_URL)

@app.get("/db_test")
async def root():
    with Session(engine) as session:
        res = [str(row) for row in session.execute(sqlalchemy.text("SELECT version();")).all()]
        print(", ".join(res))
        return {"message": res}
        
    return {"message": "Hello World"}


@app.get("/testsss")
async def root():
    return {"message": "Hello World"}