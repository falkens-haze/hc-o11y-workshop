FROM python:3.12-slim

WORKDIR /app

# Install dependencies at build time — attendees never touch pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py .

ENTRYPOINT ["python", "generate.py"]
