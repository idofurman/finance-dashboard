FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY frontend/ ./frontend/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python3", "app.py"]
