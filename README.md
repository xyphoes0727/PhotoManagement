# PhotoManagement

PhotoManagement is a photo organization app with three services:

- A Django backend for photo, album, search, and stats APIs
- A FastAPI ML engine for captioning, face detection, text embeddings, and album tagging
- A React frontend for browsing, uploading, searching, and managing photos

The app uses PostgreSQL for persistence, S3 for image storage, Pinecone for vector search, and AI services for automatic image understanding.

## Features

- Upload photos and automatically generate captions
- Detect faces and store face embeddings
- Search photos with natural language queries
- Suggest album tags from image captions
- List photos and albums from the web UI
- Fetch photo images through presigned S3 URLs

## Project Structure

- `backend/` - Django API and photo service logic
- `frontend/` - React single-page app
- `ml_engine/` - FastAPI service for captioning and embedding tasks
- `setup.md` - PostgreSQL bootstrap notes

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- PostgreSQL
- Access to S3, Pinecone, and OpenAI credentials for full functionality

## Configuration

Create a `.env` file in `backend/` for the Django service and another `.env` file in `ml_engine/` for the ML service.

Common backend environment variables:

- `DJANGO_SECRET`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `PINECONE_API_KEY`
- `PINECONE_IMAGE_INDEX_HOST`
- `PINECONE_FACE_INDEX_HOST`

Common ML engine environment variables:

- `OPENAI_API_KEY`

The frontend uses `REACT_APP_API_URL` when you want to point it at a backend host other than `http://localhost:9000`.

## Database Setup

The included `setup.md` file shows the PostgreSQL bootstrap steps used by the project. In short, create the database, user, and schema, then run Django migrations from the backend directory.

## Installation

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
```

### 2. ML Engine

```bash
cd ml_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Running the Services

Run each service in its own terminal:

```bash
# Backend
cd backend
python -m uvicorn photo_backend.asgi:application --host 0.0.0.0 --port 9000 --reload

# ML engine
cd ml_engine
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm start
```

By default, the frontend talks to the backend at `http://localhost:9000`.

## API Endpoints

Backend routes are mounted under `/api/`.

- `POST /api/query/` - natural language photo search
- `POST /api/upload/` - upload and process an image
- `POST /api/caption/` - generate an image caption
- `POST /api/face/` - detect faces in an image
- `POST /api/albumization/` - generate album tags from a caption
- `GET /api/photos/` - list photos
- `GET /api/photos/<photo_id>/` - get photo details
- `GET /api/albums/` - list albums
- `GET /api/albums/<album_id>/` - get album details
- `GET /api/albums/<album_id>/photos/` - list photos in an album
- `GET /api/stats/` - fetch dashboard statistics

## Benchmark Suite

The repository includes a standalone benchmark runner in `backend/benchmarks/` for measuring indexing throughput, retrieval latency, and retrieval quality.

Example usage from the `backend/` directory:

```bash
python benchmark.py \
	--dataset-dir /path/to/images \
	--queries-file benchmarks/examples/benchmark_queries.example.json \
	--ground-truth-file benchmarks/examples/benchmark_ground_truth.example.json \
	--number-of-images 100 \
	--number-of-queries 10 \
	--warmup-iterations 2 \
	--repeated-runs 5 \
	--output-json benchmark_results.json \
	--output-csv benchmark_query_timings.csv
```

The runner writes a JSON summary, a per-query CSV, and reuses a persistent cache in `backend/.benchmark_cache/` so caption and embedding results do not need to be regenerated on every run.

## Notes

- The upload flow can continue even if S3 or Pinecone operations fail, but the request will still return the processing result when possible.
- The ML engine loads large models at startup, so the first launch can take time.
- Some frontend routes depend on backend endpoints and external services being available.

## License

See [LICENSE](LICENSE) for project licensing details.