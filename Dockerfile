FROM python:3.11-slim
WORKDIR /app

# 安装系统依赖（matplotlib 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libfreetype6-dev libpng-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY . .

EXPOSE 5001
CMD python run.py
