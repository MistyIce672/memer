# Container image for the web app (web/). The browser does all the MediaPipe
# work, so the image only needs the FastAPI server — no opencv/mediapipe.
FROM python:3.12-slim

WORKDIR /app

# Install web deps first for better layer caching.
COPY web/requirements.txt web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt

# App code + the sample memes that seed.py imports on first run.
COPY web/ web/
COPY memes/ memes/

# Uploaded files + Mongo are external state:
#   * MONGO_URI (set in the deploy .env) must point at a reachable MongoDB.
#   * web/storage is mounted as a volume so uploads survive redeploys.
ENV MONGO_URI="mongodb://localhost:27017" \
    MONGO_DB="meme_app"

WORKDIR /app/web
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
