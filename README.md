# Books API

> A production-ready RESTful API for managing books, authors, and genres with user authentication, reviews, Redis caching, rate limiting, OAuth social login, GraphQL, and real-time WebSocket updates.

[![Live API](https://img.shields.io/badge/Live_API-Railway-blueviolet?logo=railway)](https://books-api-fastapi-production-4ebc.up.railway.app/docs)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![Tests](https://img.shields.io/badge/tests-250%20passing-success)](https://github.com/FabioPita18/books-api-fastapi/actions)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)

## 🌐 Live Demo

**Try the API now:** [https://books-api-fastapi-production-4ebc.up.railway.app](https://books-api-fastapi-production-4ebc.up.railway.app)

| Resource | URL |
|----------|-----|
| Swagger UI | [/docs](https://books-api-fastapi-production-4ebc.up.railway.app/docs) |
| ReDoc | [/redoc](https://books-api-fastapi-production-4ebc.up.railway.app/redoc) |
| GraphQL Playground | [/graphql](https://books-api-fastapi-production-4ebc.up.railway.app/graphql) |
| Health Check | [/health](https://books-api-fastapi-production-4ebc.up.railway.app/health) |
| Books API | [/api/v1/books/](https://books-api-fastapi-production-4ebc.up.railway.app/api/v1/books/) |
| Authors API | [/api/v1/authors/](https://books-api-fastapi-production-4ebc.up.railway.app/api/v1/authors/) |
| Genres API | [/api/v1/genres/](https://books-api-fastapi-production-4ebc.up.railway.app/api/v1/genres/) |
| WebSocket | ws://books-api-fastapi-production-4ebc.up.railway.app/ws/{channel} |

## 📋 Overview

A modern, well-documented RESTful API built with FastAPI for managing a collection of books, authors, and genres. Features include user authentication (email/password + OAuth), book reviews and ratings, intelligent caching, rate limiting, GraphQL endpoint, real-time WebSocket updates, and auto-generated interactive documentation.

## 🎯 Problem Statement

Developers and applications need a reliable, performant API to access book data with:

- User authentication and personalized features
- Review and rating system for community engagement
- Fast response times for frequently accessed data
- Protection against abuse through rate limiting
- Clear, interactive documentation
- Type-safe responses
- Production-ready reliability

## ✨ Solution

A FastAPI-based API providing:

- **User System**: Email/password registration, JWT authentication, OAuth (Google, GitHub)
- **Reviews & Ratings**: Users can review and rate books with aggregated scores
- **GraphQL API**: Full GraphQL endpoint with queries and mutations via Strawberry
- **Real-Time Updates**: WebSocket channels for live book and review notifications
- **Fast Performance**: Async operations with Redis caching for popular queries
- **Rate Limiting**: Tiered access (100 req/hour free, 1000 req/hour with API key)
- **Auto Documentation**: Interactive Swagger UI, ReDoc, and GraphQL Playground
- **Type Safety**: Pydantic models for request/response validation
- **Production Ready**: Containerized, tested, and CI/CD enabled

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.109.0
- **Language**: Python 3.11+
- **Database**: PostgreSQL 16
- **Caching**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **GraphQL**: Strawberry GraphQL
- **WebSocket**: FastAPI WebSocket with channel subscriptions
- **Authentication**: JWT (PyJWT), OAuth2 (Authlib)
- **Testing**: pytest with pytest-cov
- **Validation**: Pydantic v2
- **Rate Limiting**: slowapi
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Deployment**: Railway
- **Documentation**: OpenAPI (Swagger UI), GraphQL Playground

## 🚀 Key Features

### Current Features

- [x] Complete CRUD operations for books, authors, and genres
- [x] Advanced search and filtering
- [x] Redis caching for popular queries
- [x] Rate limiting (100 free, 1000 with API key)
- [x] API key authentication for write operations
- [x] **User registration and authentication** (email/password)
- [x] **JWT token management** (access + refresh tokens)
- [x] **OAuth social login** (Google, GitHub)
- [x] **Book reviews and ratings system**
- [x] **Rating aggregations** (average rating, review count)
- [x] **User profiles** with public/private views
- [x] **GraphQL API** with queries and mutations (Strawberry)
- [x] **WebSocket real-time updates** with channel subscriptions
- [x] **Event broadcasting** for books and reviews
- [x] Auto-generated OpenAPI documentation
- [x] 253+ tests with high coverage
- [x] Docker containerization
- [x] CI/CD pipeline with GitHub Actions
- [x] Database migrations with Alembic

### All Planned Features Complete! 🎉

This project has implemented all originally planned features including:
- OAuth2 authentication ✓
- Book recommendations algorithm ✓
- Review and rating system ✓
- Elasticsearch for advanced search ✓
- GraphQL endpoint ✓
- WebSocket for real-time updates ✓

## 📡 API Endpoints

### Authentication

```
POST   /api/v1/auth/register        # Register new user
POST   /api/v1/auth/login           # Login (returns JWT tokens)
POST   /api/v1/auth/refresh         # Refresh access token
POST   /api/v1/auth/logout          # Logout (invalidate token)
GET    /api/v1/auth/me              # Get current user info
GET    /api/v1/auth/google          # Google OAuth login
GET    /api/v1/auth/google/callback # Google OAuth callback
GET    /api/v1/auth/github          # GitHub OAuth login
GET    /api/v1/auth/github/callback # GitHub OAuth callback
```

### Users

```
GET    /api/v1/users/me             # Get current user profile
PUT    /api/v1/users/me             # Update profile (name, bio, avatar)
PUT    /api/v1/users/me/password    # Change password
GET    /api/v1/users/me/reviews     # Get current user's reviews
GET    /api/v1/users/{id}           # Get public user profile
```

### Books

```
GET    /api/v1/books/               # List all books (paginated, filterable)
GET    /api/v1/books/{id}           # Get book details (includes avg rating)
GET    /api/v1/books/search         # Search books with filters
GET    /api/v1/books/top-rated      # Get top-rated books
POST   /api/v1/books/               # Create new book (requires API key)
PUT    /api/v1/books/{id}           # Update book (requires API key)
DELETE /api/v1/books/{id}           # Delete book (requires API key)
```

### Reviews

```
GET    /api/v1/books/{book_id}/reviews     # List reviews for a book
POST   /api/v1/books/{book_id}/reviews     # Create review (auth required)
GET    /api/v1/reviews/{id}                # Get review details
PUT    /api/v1/reviews/{id}                # Update review (owner only)
DELETE /api/v1/reviews/{id}                # Delete review (owner/admin)
GET    /api/v1/books/{book_id}/rating-stats # Get rating statistics
GET    /api/v1/users/{user_id}/reviews     # Get user's reviews
POST   /api/v1/reviews/{id}/report         # Report a review
```

### Authors

```
GET    /api/v1/authors/             # List all authors
GET    /api/v1/authors/{id}         # Get author details
GET    /api/v1/authors/{id}/books   # Get books by author (paginated)
POST   /api/v1/authors/             # Create author (requires API key)
PUT    /api/v1/authors/{id}         # Update author (requires API key)
DELETE /api/v1/authors/{id}         # Delete author (requires API key)
```

### Genres

```
GET    /api/v1/genres/              # List all genres
GET    /api/v1/genres/{id}          # Get genre details
GET    /api/v1/genres/{id}/books    # Get books in genre (paginated)
POST   /api/v1/genres/              # Create genre (requires API key)
PUT    /api/v1/genres/{id}          # Update genre (requires API key)
DELETE /api/v1/genres/{id}          # Delete genre (requires API key)
```

### API Keys (Admin)

```
GET    /api/v1/api-keys/            # List all API keys (requires auth)
POST   /api/v1/api-keys/            # Create new API key (requires auth)
DELETE /api/v1/api-keys/{id}        # Revoke API key (requires auth)
```

### GraphQL

```
GET/POST /graphql                   # GraphQL endpoint with Playground
```

### WebSocket

```
WS     /ws/{channel}                # Subscribe to channel (books, reviews, book:1, user:1)
GET    /ws/stats                    # Get WebSocket connection statistics
```

### Documentation

```
GET    /docs                        # Swagger UI
GET    /redoc                       # ReDoc documentation
GET    /graphql                     # GraphQL Playground
GET    /openapi.json                # OpenAPI schema
```

## Example Requests

**Register a new user:**

```bash
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "bookworm", "password": "SecurePass123"}'
```

**Login and get JWT token:**

```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePass123"
```

**Create a review (authenticated):**

```bash
curl -X POST "http://localhost:8001/api/v1/books/1/reviews" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{"rating": 5, "comment": "An absolute masterpiece!"}'
```

**Get a book (no auth required):**

```bash
curl -X GET "http://localhost:8001/api/v1/books/1"
```

**Search books with filters:**

```bash
curl -X GET "http://localhost:8001/api/v1/books/search?author=orwell&min_year=1940"
```

### Example Response (Book with Rating)

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "isbn": "978-0135957059",
  "published_date": "2019-09-13",
  "description": "Your journey to mastery",
  "average_rating": 4.7,
  "review_count": 23,
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

## 📊 GraphQL API

The API provides a full GraphQL endpoint at `/graphql` with an interactive playground.

### Example Queries

**List books with pagination:**

```graphql
query {
  books(page: 1, perPage: 10) {
    items {
      id
      title
      isbn
      averageRating
      authors {
        id
        name
      }
      genres {
        id
        name
      }
    }
    total
    pages
  }
}
```

**Get a single book with reviews:**

```graphql
query {
  book(id: 1) {
    id
    title
    description
    averageRating
    reviewCount
    reviews(page: 1, perPage: 5) {
      items {
        rating
        title
        content
        user {
          fullName
        }
      }
    }
  }
}
```

**Get current user (authenticated):**

```graphql
query {
  me {
    id
    email
    fullName
    createdAt
  }
}
```

### Example Mutations

**Login:**

```graphql
mutation {
  login(input: {
    email: "user@example.com"
    password: "SecurePass123"
  }) {
    accessToken
    refreshToken
    user {
      id
      email
    }
  }
}
```

**Create a review (authenticated):**

```graphql
mutation {
  createReview(bookId: 1, input: {
    rating: 5
    title: "Excellent book!"
    content: "Highly recommended for all developers."
  }) {
    id
    rating
    title
    createdAt
  }
}
```

## 🔌 WebSocket Real-Time Updates

Connect to WebSocket channels to receive real-time updates when books or reviews are created, updated, or deleted.

### Available Channels

| Channel | Description |
|---------|-------------|
| `books` | All book events (create, update, delete) |
| `reviews` | All review events |
| `book:{id}` | Events for a specific book |
| `user:{id}` | Private user notifications (requires auth) |

### Connection Example (JavaScript)

```javascript
// Connect to the books channel
const ws = new WebSocket('ws://localhost:8001/ws/books');

// With authentication
const token = 'your-jwt-token';
const wsAuth = new WebSocket(`ws://localhost:8001/ws/user:1?token=${token}`);

ws.onopen = () => {
  console.log('Connected to books channel');

  // Send ping to keep connection alive
  ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));

  // Subscribe to additional channel
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'reviews' }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'connected':
      console.log(`Connected to ${data.channel}, authenticated: ${data.authenticated}`);
      break;
    case 'book.created':
      console.log('New book created:', data.data);
      break;
    case 'book.updated':
      console.log('Book updated:', data.data);
      break;
    case 'review.created':
      console.log('New review:', data.data);
      break;
    case 'pong':
      console.log('Pong received');
      break;
  }
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Event Types

| Event | Description |
|-------|-------------|
| `book.created` | A new book was added |
| `book.updated` | A book was modified |
| `book.deleted` | A book was removed |
| `review.created` | A new review was posted |
| `review.updated` | A review was modified |
| `review.deleted` | A review was removed |
| `user.notification` | Private user notification |

## 💻 Local Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Or: PostgreSQL 16+ and Redis 7+ (for local setup without Docker)

### Quick Start

```bash
# Clone repository
git clone https://github.com/FabioPita18/books-api-fastapi.git
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

API will be available at `http://localhost:8001`
Documentation at `http://localhost:8001/docs`

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

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
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
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic Settings configuration
│   ├── database.py          # SQLAlchemy engine and session
│   ├── dependencies.py      # FastAPI dependency injection
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── genre.py
│   │   ├── user.py          # User model with OAuth support
│   │   ├── review.py        # Review model
│   │   └── api_key.py       # API key model
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── genre.py
│   │   ├── user.py          # User schemas
│   │   ├── review.py        # Review schemas
│   │   └── api_key.py
│   ├── routers/             # API route handlers
│   │   ├── books.py
│   │   ├── authors.py
│   │   ├── genres.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── users.py         # User profile routes
│   │   ├── reviews.py       # Review routes
│   │   ├── api_keys.py      # API key management
│   │   └── websocket.py     # WebSocket endpoint
│   ├── graphql/             # GraphQL schema (Strawberry)
│   │   ├── schema.py        # Main schema
│   │   ├── types.py         # GraphQL types
│   │   ├── queries.py       # GraphQL queries
│   │   └── mutations.py     # GraphQL mutations
│   └── services/            # Business logic
│       ├── cache.py         # Redis caching
│       ├── rate_limiter.py  # Rate limiting with slowapi
│       ├── auth.py          # API key authentication
│       ├── security.py      # Password hashing, JWT tokens
│       ├── oauth.py         # OAuth providers (Google, GitHub)
│       ├── ratings.py       # Rating aggregation service
│       ├── websocket.py     # WebSocket connection manager
│       └── events.py        # Event publishing system
├── tests/                   # pytest test suite (253+ tests)
│   ├── conftest.py          # Shared fixtures
│   ├── test_books.py
│   ├── test_authors.py
│   ├── test_genres.py
│   ├── test_search.py       # Search & filtering tests
│   ├── test_auth.py         # API key authentication tests
│   ├── test_user_auth.py    # User registration/login tests
│   ├── test_auth_social.py  # OAuth tests
│   ├── test_users.py        # User profile tests
│   ├── test_reviews.py      # Review CRUD tests
│   ├── test_graphql.py      # GraphQL endpoint tests
│   ├── test_websocket.py    # WebSocket tests
│   └── test_events.py       # Event system tests
├── alembic/                 # Database migrations
├── scripts/
│   └── seed_data.py         # Sample data seeder
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Rate Limiting Tiers

| Endpoint Type           | Rate Limit | Notes            |
| ----------------------- | ---------- | ---------------- |
| Default (GET)           | 100/minute | IP-based         |
| Search                  | 60/minute  | IP-based         |
| Write (POST/PUT/DELETE) | 30/minute  | Requires API key |

### Caching Strategy

- **Popular books**: 5 minutes TTL
- **Search results**: 2 minutes TTL
- **Author details**: 10 minutes TTL
- **Genre listings**: 15 minutes TTL

### Authentication

| Method | Description |
|--------|-------------|
| Email/Password | Traditional registration with secure password hashing |
| JWT Tokens | Access tokens (30 min) + Refresh tokens (7 days) |
| Google OAuth | Sign in with Google account |
| GitHub OAuth | Sign in with GitHub account |

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

**Fabio Pita**

- GitHub: [@FabioPita18](https://github.com/FabioPita18)
- LinkedIn: [Fabio Miguel Pita](https://www.linkedin.com/in/fabio-pita-455b83212/)

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Database with [PostgreSQL](https://www.postgresql.org/)
- Caching with [Redis](https://redis.io/)
- Testing with [pytest](https://pytest.org/)

---

**Built by [Fabio Pita](https://github.com/FabioPita18)** | **[Live API](https://books-api-fastapi-production-4ebc.up.railway.app/docs)** | **[GitHub](https://github.com/FabioPita18/books-api-fastapi)**
