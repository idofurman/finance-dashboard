FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
CMD ["python3", "app.py"]
