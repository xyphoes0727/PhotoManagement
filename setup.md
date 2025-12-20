-- ===============================
-- PostgreSQL setup for Django
-- ===============================
-- Run everything as postgres
-- ===============================

-- 1. Create database and user
CREATE DATABASE app_db;

CREATE USER app_user
WITH PASSWORD 'mypwd';

-- 2. Allow Django to connect and create objects
GRANT CONNECT, CREATE ON DATABASE app_db TO app_user;

-- 3. Switch to the app database
\c app_db

-- 4. Create application schema
CREATE SCHEMA app AUTHORIZATION app_user;

-- 5. Let Django use this schema by default
ALTER ROLE app_user SET search_path = app;

-- 6. Grant schema permissions
GRANT USAGE, CREATE ON SCHEMA app TO app_user;

-- 7. Default privileges for Django migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA app
GRANT ALL ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA app
GRANT ALL ON SEQUENCES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA app
GRANT ALL ON FUNCTIONS TO app_user;

cd backend/photo_backend/
python manage.py makemigrations
python manage.py migrate