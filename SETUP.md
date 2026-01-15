# Books API - Setup Guide

This guide walks you through setting up the Books API for local development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10 or later)
  ```bash
  docker --version
  ```

- **Docker Compose** (version 2.0 or later)
  ```bash
  docker-compose --version
  ```

- **Python 3.12+** (for running without Docker)
  ```bash
  python3 --version
  ```

- **Git** (for version control)
  ```bash
  git --version
  ```

## Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/books-api-fastapi.git
cd books-api-fastapi
```

### Step 2: Create Your Environment File

```bash
cp .env.example .env
```

### Step 3: Generate Secure Secrets

Generate a secret key:
```bash
openssl rand -hex 32
```

Generate a database password:
```bash
openssl rand -base64 24
```

### Step 4: Update Your .env File

Open `.env` in your editor and replace the placeholder values:

```bash
# Replace this:
SECRET_KEY=REPLACE_WITH_YOUR_GENERATED_SECRET_KEY

# With your generated value (example):
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# Replace this:
POSTGRES_PASSWORD=REPLACE_WITH_YOUR_GENERATED_PASSWORD

# With your generated value (example):
POSTGRES_PASSWORD=xK9mN2pQ7rS4tU1vW6xY3zA

# Also update DATABASE_URL with your password:
DATABASE_URL=postgresql://books_admin:xK9mN2pQ7rS4tU1vW6xY3zA@localhost:5433/books_production
```

### Step 5: Start the Services

```bash
docker-compose up -d
```

This starts:
- **API** on port `8001`
- **PostgreSQL** on port `5433`

### Step 6: Run Database Migrations

```bash
# First time: Create initial migration
docker-compose exec api alembic revision --autogenerate -m "Initial migration"

# Apply migrations
docker-compose exec api alembic upgrade head
```

### Step 7: Seed Sample Data (Optional)

```bash
docker-compose exec api python scripts/seed_data.py
```

### Step 8: Access the API

- **API Documentation (Swagger)**: http://localhost:8001/docs
- **Alternative Docs (ReDoc)**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health
- **API Root**: http://localhost:8001/

## Verify Your Setup

### Check Service Health

```bash
# Check if containers are running
docker-compose ps

# Check API health
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "Books API",
  "version": "v1"
}
```

### Test API Endpoints

```bash
# List all books
curl http://localhost:8001/api/v1/books/

# Create a new author
curl -X POST http://localhost:8001/api/v1/authors/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Author", "bio": "A test author"}'

# Create a new book
curl -X POST http://localhost:8001/api/v1/books/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Book", "isbn": "978-0-13-468599-1"}'
```

## Development Without Docker

If you prefer to run without Docker:

### Step 1: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 3: Set Up PostgreSQL

You'll need a local PostgreSQL instance. Create the database:

```sql
CREATE USER books_admin WITH PASSWORD 'your_password';
CREATE DATABASE books_production OWNER books_admin;
```

### Step 4: Update .env for Local Database

```bash
DATABASE_URL=postgresql://books_admin:your_password@localhost:5432/books_production
```

### Step 5: Run Migrations

```bash
alembic upgrade head
```

### Step 6: Start the Server

```bash
uvicorn app.main:app --reload --port 8001
```

## Common Commands

### Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Restart a service
docker-compose restart api

# Reset everything (including data)
docker-compose down -v
```

### Database Commands

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply all migrations
docker-compose exec api alembic upgrade head

# Rollback one migration
docker-compose exec api alembic downgrade -1

# Show migration history
docker-compose exec api alembic history

# Show current migration
docker-compose exec api alembic current
```

### Testing Commands

```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/test_books.py

# Run tests in verbose mode
docker-compose exec api pytest -v
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs api

# Common issue: Missing environment variables
# Solution: Ensure .env file exists and has all required values
```

### Database Connection Refused

```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check PostgreSQL logs
docker-compose logs db

# Common issue: Wrong port or credentials
# Solution: Verify DATABASE_URL matches your .env settings
```

### Migration Errors

```bash
# Reset migrations (development only!)
docker-compose exec api alembic downgrade base
docker-compose exec api alembic upgrade head

# If that fails, reset the database
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8001
lsof -i :5433

# Solution: Change ports in .env
API_PORT=8002
POSTGRES_PORT=5434
```

## Project Structure

```
books-api-fastapi/
├── app/                    # Application code
│   ├── config.py          # Configuration management
│   ├── database.py        # Database setup
│   ├── main.py            # FastAPI application
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # API endpoints
│   └── schemas/           # Pydantic schemas
├── tests/                  # Test suite
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── docker-compose.yml     # Docker services
├── Dockerfile             # Container build
├── .env                   # Your local config (not in Git)
├── .env.example           # Config template (in Git)
└── requirements.txt       # Dependencies
```

## What's Next?

After completing setup:

1. **Explore the API**: Visit http://localhost:8001/docs
2. **Run the tests**: `docker-compose exec api pytest`
3. **Read the code**: Start with `app/main.py`
4. **Add features**: Create new routers in `app/routers/`

## Phase 2 Preview

The following features will be added in Phase 2:
- **Redis** for caching and session storage
- **Rate limiting** to prevent abuse
- **API key authentication**
- **Response caching** for performance

See the commented sections in `docker-compose.yml` and `app/config.py` for the configuration that will be enabled.

## Getting Help

- **Documentation**: Check the `/docs` endpoint
- **Issues**: Open a GitHub issue
- **Security**: See `SECURITY.md` for security guidelines
