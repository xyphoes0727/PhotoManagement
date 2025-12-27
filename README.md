# PhotoManagement

PYTHONPATH="$(pwd)/.." python -m uvicorn photo_backend.asgi:application --host 0.0.0.0 --port 9000 --reload
PYTHONPATH="${pwd}/.." python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
