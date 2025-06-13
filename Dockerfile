FROM python:3.11-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install -r requirements.txt
COPY server .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
