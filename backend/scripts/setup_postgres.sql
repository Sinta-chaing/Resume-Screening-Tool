-- Run once as a PostgreSQL superuser (e.g. psql -U postgres -f scripts/setup_postgres.sql)
-- Replace DB name/user/password to match backend/.env

CREATE DATABASE resume_screener;

-- Connect to the new database before running the next line:
-- \c resume_screener

CREATE EXTENSION IF NOT EXISTS vector;
