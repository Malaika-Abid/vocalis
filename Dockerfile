FROM python:3.10-slim

WORKDIR /app

# Install essential audio library system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port (7860 is standard for Hugging Face Spaces, Render injects its own $PORT)
ENV PORT=7860
EXPOSE 7860

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "7860"]

