from fastapi import FastAPI
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

app = FastAPI()
DATABASE_URL = "postgresql://dashboard:dashboard@db:5432/dashboard"
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