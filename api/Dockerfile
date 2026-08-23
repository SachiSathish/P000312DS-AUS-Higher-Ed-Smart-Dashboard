FROM python:3.12-slim

WORKDIR /api
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r /api/requirements.txt

CMD ["fastapi", "dev", "app.py", "--host", "0.0.0.0", "--port", "80"]