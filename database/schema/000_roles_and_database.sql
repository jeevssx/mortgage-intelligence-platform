-- One-time setup: roles and database. Run as a PostgreSQL superuser, once per environment.
--
--   psql -U postgres -v owner_password='...' -v app_password='...' -f database/schema/000_roles_and_database.sql
--
-- Roles:
--   mortgage_owner  owns the database and schema; runs migrations (DDL).
--   mortgage_app    used by services at runtime; DML only (SELECT/INSERT/UPDATE/DELETE).
-- Passwords are passed in as psql variables and are never stored in this file.

\set ON_ERROR_STOP on

SELECT format('CREATE ROLE mortgage_owner LOGIN PASSWORD %L', :'owner_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mortgage_owner') \gexec

SELECT format('CREATE ROLE mortgage_app LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mortgage_app') \gexec

SELECT 'CREATE DATABASE mortgage_intel OWNER mortgage_owner ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mortgage_intel') \gexec

\connect mortgage_intel

ALTER SCHEMA public OWNER TO mortgage_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

GRANT CONNECT ON DATABASE mortgage_intel TO mortgage_app;
GRANT USAGE ON SCHEMA public TO mortgage_app;

-- Tables created later by mortgage_owner (via migrations) are automatically usable by mortgage_app.
ALTER DEFAULT PRIVILEGES FOR ROLE mortgage_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mortgage_app;
ALTER DEFAULT PRIVILEGES FOR ROLE mortgage_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO mortgage_app;
