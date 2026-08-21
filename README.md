# P000312DS-AUS-Higher-Ed-Smart-Dashboard
Main repo for our project.



### Docker container commands
Start up: `docker compose up -d`

Force a rebuild: `docker compose up -d --build`

Access the environment: `docker compose exec api bash`

View logs: `docker compose logs APIService`

Shut down: `docker compose down`

You should only need to rebuild if you add new services or python modules, you should just be able to use compose up and down without rebuild

### Sources and Attribution
- fastapi
- uvicorn
- uv
- sqlalchemy
- alembic
- pydantic
- psycopg2-binary
- duckdb
- pandas
- openpyxl 