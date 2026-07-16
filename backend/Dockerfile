FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /venv /venv
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENV PATH="/venv/bin:$PATH"
CMD ["python3", "app.py"]
