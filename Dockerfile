FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

ENV PORT=10000

CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
