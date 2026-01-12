# Books API with Rate Limiting

> A production-ready RESTful API for managing books with Redis caching, rate limiting, and comprehensive OpenAPI documentation.

[![Live API](https://img.shields.io/badge/API-live-brightgreen)](https://books-api.railway.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-passing-success)](https://github.com/yourusername/books-api-fastapi/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://github.com/yourusername/books-api-fastapi)

## 📋 Overview

A modern, well-documented RESTful API built with FastAPI for managing a collection of books, authors, and genres. Features include intelligent caching, rate limiting, API key authentication, and auto-generated interactive documentation.

## 🎯 Problem Statement

Developers and applications need a reliable, performant API to access book data with:
- Fast response times for frequently accessed data
- Protection against abuse through rate limiting
- Clear, interactive documentation
- Type-safe responses
- Production-ready reliability

## ✨ Solution

A FastAPI-based API providing:
- **Fast Performance**: Async operations with Redis caching for popular queries
- **Rate Limiting**: Tiered access (100 req/hour free, 1000 req/hour with API key)
- **Auto Documentation**: Interactive Swagger UI and ReDoc
- **Type Safety**: Pydantic models for request/response validation
- **Production Ready**: Containerized, tested, and CI/CD enabled

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.109.0
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **Caching**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Testing**: pytest with pytest-cov
- **Validation**: Pydantic v2
- **Rate Limiting**: slowapi
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Deployment**: Railway
- **Documentation**: OpenAPI (Swagger UI)

## 🚀 Key Features

### Current (MVP)
- [x] Complete CRUD operations for books, authors, and genres
- [x] Advanced search and filtering
- [x] Redis caching for popular queries
- [x] Rate limiting (100 free, 1000 with API key)
- [x] API key authentication
- [x] Auto-generated OpenAPI documentation
- [x] 85%+ test coverage
- [x] Docker containerization
- [x] CI/CD pipeline with GitHub Actions
- [x] Database migrations with Alembic

### Future Enhancements
- [ ] OAuth2 authentication
- [ ] Pagination for large result sets
- [ ] Book recommendations algorithm
- [ ] Review and rating system
- [ ] Elasticsearch for advanced search
- [ ] GraphQL endpoint

## 📡 API Endpoints

### Books
```
GET    /api/books/                # List all books (paginated)
GET    /api/books/{id}/           # Get book details
GET    /api/books/search/         # Search books by title/author
POST   /api/books/                # Create new book (requires API key)
PUT    /api/books/{id}/           # Update book (requires API key)
DELETE /api/books/{id}/           # Delete book (requires API key)
```

### Authors
```
GET    /api/authors/              # List all authors
GET    /api/authors/{id}/         # Get author details
GET    /api/authors/{id}/books/   # Get books by author
POST   /api/authors/              # Create author (requires API key)
```

### Genres
```
GET    /api/genres/               # List all genres
GET    /api/genres/{id}/          # Get genre details
GET    /api/genres/{id}/books/    # Get books in genre
```

### Documentation
```
GET    /docs                      # Swagger UI
GET    /redoc                     # ReDoc documentation
GET    /openapi.json              # OpenAPI schema
```

## 📸 API Documentation

![Swagger UI](docs/screenshots/swagger-ui.png)

### Example Request
```bash
curl -X GET "https://books-api.railway.app/api/books/1" \
  -H "X-API-Key: your-api-key-here"
```

### Example Response
```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "isbn": "978-0135957059",
  "published_date": "2019-09-13",
  "description": "Your journey to mastery",
  "authors": [
    {
      "id": 1,
      "name": "David Thomas"
    },
    {
      "id": 2,
      "name": "Andrew Hunt"
    }
  ],
  "genres": [
    {
      "id": 1,
      "name": "Programming"
    }
  ],
  "created_at": "2026-01-13T10:00:00Z"
}
```

## 💻 Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Quick Start
```bash
# Clone repository
git clone https://github.com/yourusername/books-api-fastapi.git
cd books-api-fastapi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Seed database (optional)
python scripts/seed_data.py

# Run development server
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`  
Documentation at `http://localhost:8000/docs`

### Docker Setup (Recommended)
```bash
# Start all services
docker-compose up --build

# Run migrations
docker-compose exec api alembic upgrade head

# Seed database
docker-compose exec api python scripts/seed_data.py

# View logs
docker-compose logs -f api
```

## 🧪 Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_books.py

# Run with verbose output
pytest -v
```

View coverage report at `htmlcov/index.html`

## 🔐 Environment Variables
```bash
# .env.example
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
RATE_LIMIT_FREE=100  # requests per hour
RATE_LIMIT_PREMIUM=1000  # requests per hour

# Security
SECRET_KEY=your-secret-key-here
API_KEY_HEADER=X-API-Key
```

## 📦 Deployment

### Railway (Recommended)

1. **Create Railway project**
```bash
   railway init
```

2. **Add PostgreSQL and Redis**
```bash
   railway add postgresql
   railway add redis
```

3. **Set environment variables** in Railway dashboard

4. **Deploy**
```bash
   railway up
```

### Docker Deployment
```bash
# Build image
docker build -t books-api:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  books-api:latest
```

## 📁 Project Structure
```
books-api-fastapi/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── book.py
│   │   ├── author.py
│   │   └── genre.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── book.py
│   │   ├── author.py
│   │   └── genre.py
│   ├── routers/             # API endpoints
│   │   ├── books.py
│   │   ├── authors.py
│   │   └── genres.py
│   ├── services/            # Business logic
│   │   ├── cache.py         # Redis caching
│   │   └── rate_limit.py    # Rate limiting
│   └── utils/               # Helper functions
├── tests/
│   ├── test_books.py
│   ├── test_authors.py
│   └── test_cache.py
├── alembic/                 # Database migrations
├── scripts/
│   └── seed_data.py         # Sample data
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Rate Limiting Tiers

| Tier | Requests/Hour | Authentication |
|------|---------------|----------------|
| Free | 100 | None (IP-based) |
| Premium | 1,000 | API Key required |

### Caching Strategy

- **Popular books**: 5 minutes TTL
- **Search results**: 2 minutes TTL
- **Author details**: 10 minutes TTL
- **Genre listings**: 15 minutes TTL

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Fabio [Your Last Name]**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/yourprofile)
- Portfolio: [fabio-portfolio.vercel.app](https://fabio-portfolio.vercel.app)

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Database with [PostgreSQL](https://www.postgresql.org/)
- Caching with [Redis](https://redis.io/)
- Testing with [pytest](https://pytest.org/)

---

**API Status**: ✅ Live at https://books-api.railway.app  
**Documentation**: 📚 https://books-api.railway.app/docs
