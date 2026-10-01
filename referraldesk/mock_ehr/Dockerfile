FROM python:3.12-slim
WORKDIR /app
COPY mock_ehr/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mock_ehr/ .
EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
