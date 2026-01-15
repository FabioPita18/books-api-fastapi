I'm building a Books API with FastAPI as the first of three portfolio projects to demonstrate modern Python development skills. This is a learning project where I need to understand every decision and follow best practices.

🎯 Project Context
Repository: books-api-fastapi (already initialized on GitHub with README, LICENSE, .gitignore)
Tech Stack: FastAPI, PostgreSQL, Redis, SQLAlchemy 2.0, pytest, Docker
Timeline: 2-3 weeks (starting Jan 13, 2026)
My Level: Strong in Django, learning FastAPI, basic Docker, zero CI/CD experience
Goal: Production-ready API with 85%+ test coverage, proper DevOps practices

📋 What I Need You To Do

Phase 1: Development Environment Setup
Set up the complete development environment following Python best practices:

1. Virtual Environment Setup

   - Create and activate a Python virtual environment
   - Explain why we use virtual environments
   - Install all dependencies from requirements.txt
   - Show me how to verify installations

2. Project Structure Creation - Create this exact directory structure:
   books-api-fastapi/
   ├── app/
   │ ├── **init**.py
   │ ├── main.py # FastAPI app entry point
   │ ├── config.py # Configuration (environment variables)
   │ ├── database.py # Database connection & session
   │ ├── dependencies.py # Dependency injection functions
   │ ├── models/ # SQLAlchemy models
   │ │ ├── **init**.py
   │ │ ├── book.py
   │ │ ├── author.py
   │ │ └── genre.py
   │ ├── schemas/ # Pydantic schemas (request/response)
   │ │ ├── **init**.py
   │ │ ├── book.py
   │ │ ├── author.py
   │ │ └── genre.py
   │ ├── routers/ # API route handlers
   │ │ ├── **init**.py
   │ │ ├── books.py
   │ │ ├── authors.py
   │ │ └── genres.py
   │ ├── services/ # Business logic
   │ │ ├── **init**.py
   │ │ ├── cache.py # Redis caching
   │ │ └── rate_limit.py # Rate limiting logic
   │ └── utils/ # Helper functions
   │ └── **init**.py
   ├── tests/
   │ ├── **init**.py
   │ ├── conftest.py # pytest fixtures
   │ ├── test_books.py
   │ ├── test_authors.py
   │ └── test_genres.py
   ├── alembic/ # Database migrations (generate with alembic)
   ├── scripts/
   │ └── seed_data.py # Sample data seeding
   ├── .env.example
   ├── requirements-dev.txt # Development dependencies
   ├── Dockerfile
   ├── docker-compose.yml
   ├── pytest.ini
   └── alembic.ini

3. Environment Configuration - Create .env.example with all needed variables:
   # Application
   APP_NAME=Books API
   DEBUG=True
   API_VERSION=v1
   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/books_db
   # Redis
   REDIS_URL=redis://localhost:6379/0
   CACHE_TTL=300
   # Rate Limiting
   RATE_LIMIT_FREE=100
   RATE_LIMIT_PREMIUM=1000
   # Security
   SECRET_KEY=your-secret-key-here-generate-with-openssl
   API_KEY_HEADER=X-API-Key
   - Copy to .env for local development
   - Explain each variable's purpose
   - Show me how to generate a secure SECRET_KEY

Phase 2: Core Application Scaffold
Build the foundational files with detailed comments explaining every part:

1. app/config.py - Configuration management

   - Use Pydantic Settings for type-safe config
   - Load from environment variables
   - Teach me about the Settings pattern in FastAPI

2. app/database.py - Database setup

   - SQLAlchemy 2.0 async session setup
   - Connection pooling configuration
   - Explain the session management pattern

3. app/main.py - FastAPI application

   - Application factory pattern
   - CORS middleware setup
   - Router registration
   - Lifespan events (startup/shutdown)
   - OpenAPI documentation configuration
   - Exception handlers

4. Database Models (app/models/)

   - book.py: Book model with relationships
   - author.py: Author model (many-to-many with books)
   - genre.py: Genre model (many-to-many with books)
   - Use SQLAlchemy 2.0 declarative style
   - Add proper indexes
   - Include timestamps (created_at, updated_at)
   - Explain relationships and foreign keys

5. Pydantic Schemas (app/schemas/)
   - Request schemas (Create, Update)
   - Response schemas
   - Nested schemas for relationships
   - Use Pydantic v2 features
   - Teach me about schema validation

Phase 3: Alembic Database Migrations
Set up Alembic for database version control:

1. Initialize Alembic: alembic init alembic
2. Configure alembic.ini to use our database URL
3. Configure alembic/env.py to import our models
4. Create initial migration for all models
5. Teach me the migration workflow (create, upgrade, downgrade)

Phase 4: Basic API Endpoints (One Router First)
Implement the Books router (app/routers/books.py) as a learning example:

1. GET /api/books/ - List all books (with pagination)
2. GET /api/books/{id}/ - Get single book
3. POST /api/books/ - Create book (with validation)
4. PUT /api/books/{id}/ - Update book
5. DELETE /api/books/{id}/ - Delete book
   For each endpoint:

- Write complete docstrings
- Add request/response examples in OpenAPI
- Implement proper error handling
- Use dependency injection
- Teach me FastAPI patterns (Path, Query, Body, Depends)

Phase 5: Testing Setup
Configure pytest with best practices:

1. pytest.ini - pytest configuration
2. tests/conftest.py - Shared fixtures:
   - Test database fixture
   - Test client fixture
   - Sample data fixtures
3. tests/test_books.py - Complete test suite for books router
   - Test all CRUD operations
   - Test validation errors
   - Test database constraints
   - Teach me pytest patterns and fixtures

Phase 6: Docker Setup
Create production-ready Docker configuration:

1. Dockerfile - Multi-stage build
   - Optimized for size
   - Non-root user
   - Health check
   - Explain each instruction
2. docker-compose.yml - Local development environment
   - FastAPI app service
   - PostgreSQL service
   - Redis service
   - Named volumes for data persistence
   - Network configuration
   - Explain how services communicate

Phase 7: Development Dependencies
Create requirements-dev.txt:
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
black==24.1.1
flake8==7.0.0
mypy==1.8.0
isort==5.13.2
ipython==8.20.0

🎓 Teaching Requirements
As you implement each file:

1. Explain the "Why" - Why this pattern/approach? What problem does it solve? What are the alternatives?
2. Show Best Practices - Industry-standard patterns, Security considerations, Performance implications
3. Add Detailed Comments - Explain complex logic, Reference documentation when relevant, Include examples in docstrings
4. Teach Git Workflow - After each major phase: What should be committed? How to write good commit messages? When to push to GitHub?

📦 Dependencies Already Available
I have requirements.txt with these packages:
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.1
slowapi==0.1.9
python-jose[cryptography]==3.3.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

✅ Success Criteria
By the end of this scaffolding phase, I should have:

- Working virtual environment with all dependencies
- Complete project structure following best practices
- Fully configured FastAPI application that starts successfully
- Database models defined and migrations created
- One complete router (Books) with all CRUD endpoints
- Working test suite for that router
- Docker setup that runs the entire stack locally
- Understanding of FastAPI patterns and architecture
- Confidence to continue building the remaining routers myself

🚨 Important Notes

- Use SQLAlchemy 2.0 syntax (not the old 1.x style)
- Use Pydantic v2 features and syntax
- Follow FastAPI official docs patterns for consistency
- Explain async/await when we use it
- Set up proper logging from the start
- Include security headers and CORS properly
- Use type hints everywhere for better IDE support
- Make it production-ready, not just a tutorial example

📝 Workflow
Let's work incrementally:

1. Start with Phase 1 (environment setup)
2. After each phase, I'll test it before moving on
3. Commit working code at logical checkpoints
4. Explain what I should test/verify at each step
5. Build up complexity gradually

I'm ready to learn FastAPI properly. Let's build this with production quality from day one!
