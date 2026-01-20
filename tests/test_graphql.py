"""
GraphQL API Tests

Tests for the GraphQL endpoint including:
- Query tests (books, authors, genres, reviews, me)
- Mutation tests (CRUD operations, authentication)
- Pagination tests
- Authentication tests
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Author, Book, Genre
from app.models.review import Review
from app.models.user import User
from app.services.security import create_access_token

# =============================================================================
# Helper Functions
# =============================================================================


def graphql_query(client: TestClient, query: str, variables: dict = None, token: str = None):
    """Execute a GraphQL query and return the response."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = client.post("/graphql", json=payload, headers=headers)
    return response.json()


def get_auth_token(user: User) -> str:
    """Generate an auth token for a user."""
    return create_access_token({"sub": str(user.id)})


# =============================================================================
# Query Tests
# =============================================================================


class TestBooksQuery:
    """Tests for the books query."""

    def test_list_books_empty(self, client: TestClient):
        """Test listing books when database is empty."""
        query = """
        query {
            books {
                items {
                    id
                    title
                }
                total
                page
                pages
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["books"]["items"] == []
        assert result["data"]["books"]["total"] == 0

    def test_list_books_with_data(self, client: TestClient, sample_book: Book):
        """Test listing books with data."""
        query = """
        query {
            books {
                items {
                    id
                    title
                    isbn
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
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["books"]["total"] == 1
        assert len(result["data"]["books"]["items"]) == 1
        assert result["data"]["books"]["items"][0]["title"] == sample_book.title
        assert len(result["data"]["books"]["items"][0]["authors"]) == 1
        assert len(result["data"]["books"]["items"][0]["genres"]) == 1

    def test_list_books_pagination(self, client: TestClient, multiple_books: list[Book]):
        """Test books pagination."""
        query = """
        query($page: Int!, $perPage: Int!) {
            books(page: $page, perPage: $perPage) {
                items {
                    id
                    title
                }
                total
                page
                perPage
                pages
            }
        }
        """
        result = graphql_query(client, query, variables={"page": 1, "perPage": 5})

        assert "errors" not in result
        assert len(result["data"]["books"]["items"]) == 5
        assert result["data"]["books"]["total"] == 15
        assert result["data"]["books"]["page"] == 1
        assert result["data"]["books"]["perPage"] == 5
        assert result["data"]["books"]["pages"] == 3

    def test_get_single_book(self, client: TestClient, sample_book: Book):
        """Test getting a single book by ID."""
        query = """
        query($id: Int!) {
            book(id: $id) {
                id
                title
                isbn
                description
            }
        }
        """
        result = graphql_query(client, query, variables={"id": sample_book.id})

        assert "errors" not in result
        assert result["data"]["book"]["id"] == sample_book.id
        assert result["data"]["book"]["title"] == sample_book.title

    def test_get_book_not_found(self, client: TestClient):
        """Test getting a book that doesn't exist."""
        query = """
        query {
            book(id: 9999) {
                id
                title
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["book"] is None


class TestAuthorsQuery:
    """Tests for the authors query."""

    def test_list_authors(self, client: TestClient, sample_author: Author):
        """Test listing authors."""
        query = """
        query {
            authors {
                items {
                    id
                    name
                    bio
                }
                total
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["authors"]["total"] == 1
        assert result["data"]["authors"]["items"][0]["name"] == sample_author.name

    def test_get_single_author(self, client: TestClient, sample_author: Author):
        """Test getting a single author."""
        query = """
        query($id: Int!) {
            author(id: $id) {
                id
                name
                bio
            }
        }
        """
        result = graphql_query(client, query, variables={"id": sample_author.id})

        assert "errors" not in result
        assert result["data"]["author"]["name"] == sample_author.name


class TestGenresQuery:
    """Tests for the genres query."""

    def test_list_genres(self, client: TestClient, sample_genre: Genre):
        """Test listing genres."""
        query = """
        query {
            genres {
                items {
                    id
                    name
                    description
                }
                total
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["genres"]["total"] == 1
        assert result["data"]["genres"]["items"][0]["name"] == sample_genre.name


class TestReviewsQuery:
    """Tests for the reviews query."""

    def test_list_reviews_for_book(
        self, client: TestClient, sample_book: Book, sample_user: User, db_session: Session
    ):
        """Test listing reviews for a book."""
        # Create a review
        review = Review(
            book_id=sample_book.id,
            user_id=sample_user.id,
            rating=5,
            title="Great book!",
            content="Really enjoyed it.",
        )
        db_session.add(review)
        db_session.commit()

        query = """
        query($bookId: Int!) {
            reviews(bookId: $bookId) {
                items {
                    id
                    rating
                    title
                    content
                    user {
                        id
                        fullName
                    }
                }
                total
            }
        }
        """
        result = graphql_query(client, query, variables={"bookId": sample_book.id})

        assert "errors" not in result
        assert result["data"]["reviews"]["total"] == 1
        assert result["data"]["reviews"]["items"][0]["rating"] == 5
        assert result["data"]["reviews"]["items"][0]["title"] == "Great book!"


class TestMeQuery:
    """Tests for the me query (current user)."""

    def test_me_authenticated(self, client: TestClient, sample_user: User):
        """Test getting current user when authenticated."""
        token = get_auth_token(sample_user)

        query = """
        query {
            me {
                id
                email
                fullName
                isActive
            }
        }
        """
        result = graphql_query(client, query, token=token)

        assert "errors" not in result
        assert result["data"]["me"]["id"] == sample_user.id
        assert result["data"]["me"]["email"] == sample_user.email

    def test_me_unauthenticated(self, client: TestClient):
        """Test getting current user when not authenticated."""
        query = """
        query {
            me {
                id
                email
            }
        }
        """
        result = graphql_query(client, query)

        assert "errors" not in result
        assert result["data"]["me"] is None


# =============================================================================
# Mutation Tests
# =============================================================================


class TestAuthMutations:
    """Tests for authentication mutations."""

    def test_login_success(self, client: TestClient, sample_user: User):
        """Test successful login."""
        query = """
        mutation($input: LoginInput!) {
            login(input: $input) {
                accessToken
                refreshToken
                tokenType
                user {
                    id
                    email
                }
            }
        }
        """
        variables = {
            "input": {
                "email": sample_user.email,
                "password": "SecurePass123",
            }
        }
        result = graphql_query(client, query, variables=variables)

        assert "errors" not in result
        assert result["data"]["login"]["accessToken"] is not None
        assert result["data"]["login"]["refreshToken"] is not None
        assert result["data"]["login"]["tokenType"] == "bearer"
        assert result["data"]["login"]["user"]["email"] == sample_user.email

    def test_login_wrong_password(self, client: TestClient, sample_user: User):
        """Test login with wrong password."""
        query = """
        mutation($input: LoginInput!) {
            login(input: $input) {
                accessToken
            }
        }
        """
        variables = {
            "input": {
                "email": sample_user.email,
                "password": "WrongPassword123",
            }
        }
        result = graphql_query(client, query, variables=variables)

        assert "errors" in result

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        query = """
        mutation($input: RegisterInput!) {
            register(input: $input) {
                accessToken
                refreshToken
                user {
                    email
                    fullName
                }
            }
        }
        """
        variables = {
            "input": {
                "email": "newuser@example.com",
                "password": "NewPass123",
                "fullName": "New User",
            }
        }
        result = graphql_query(client, query, variables=variables)

        assert "errors" not in result
        assert result["data"]["register"]["accessToken"] is not None
        assert result["data"]["register"]["user"]["email"] == "newuser@example.com"


class TestBookMutations:
    """Tests for book mutations."""

    def test_create_book_authenticated(
        self, client: TestClient, sample_user: User, sample_author: Author, sample_genre: Genre
    ):
        """Test creating a book when authenticated."""
        token = get_auth_token(sample_user)

        query = """
        mutation($input: BookInput!) {
            createBook(input: $input) {
                id
                title
                isbn
                authors {
                    id
                    name
                }
                genres {
                    id
                    name
                }
            }
        }
        """
        variables = {
            "input": {
                "title": "New Test Book",
                "isbn": "1234567890123",
                "description": "A new test book",
                "pageCount": 200,
                "authorIds": [sample_author.id],
                "genreIds": [sample_genre.id],
            }
        }
        result = graphql_query(client, query, variables=variables, token=token)

        assert "errors" not in result
        assert result["data"]["createBook"]["title"] == "New Test Book"
        assert len(result["data"]["createBook"]["authors"]) == 1
        assert len(result["data"]["createBook"]["genres"]) == 1

    def test_create_book_unauthenticated(self, client: TestClient):
        """Test creating a book without authentication."""
        query = """
        mutation($input: BookInput!) {
            createBook(input: $input) {
                id
                title
            }
        }
        """
        variables = {
            "input": {
                "title": "Unauthorized Book",
            }
        }
        result = graphql_query(client, query, variables=variables)

        assert "errors" in result

    def test_update_book(
        self, client: TestClient, sample_user: User, sample_book: Book
    ):
        """Test updating a book."""
        token = get_auth_token(sample_user)

        query = """
        mutation($id: Int!, $input: BookUpdateInput!) {
            updateBook(id: $id, input: $input) {
                id
                title
                description
            }
        }
        """
        variables = {
            "id": sample_book.id,
            "input": {
                "title": "Updated Title",
                "description": "Updated description",
            }
        }
        result = graphql_query(client, query, variables=variables, token=token)

        assert "errors" not in result
        assert result["data"]["updateBook"]["title"] == "Updated Title"

    def test_delete_book(
        self, client: TestClient, sample_user: User, sample_book: Book
    ):
        """Test deleting a book."""
        token = get_auth_token(sample_user)

        query = """
        mutation($id: Int!) {
            deleteBook(id: $id)
        }
        """
        result = graphql_query(client, query, variables={"id": sample_book.id}, token=token)

        assert "errors" not in result
        assert result["data"]["deleteBook"] is True


class TestReviewMutations:
    """Tests for review mutations."""

    def test_create_review(
        self, client: TestClient, sample_user: User, sample_book: Book
    ):
        """Test creating a review."""
        token = get_auth_token(sample_user)

        query = """
        mutation($bookId: Int!, $input: ReviewInput!) {
            createReview(bookId: $bookId, input: $input) {
                id
                rating
                title
                content
                bookId
            }
        }
        """
        variables = {
            "bookId": sample_book.id,
            "input": {
                "rating": 5,
                "title": "Excellent!",
                "content": "One of the best books I've read.",
            }
        }
        result = graphql_query(client, query, variables=variables, token=token)

        assert "errors" not in result
        assert result["data"]["createReview"]["rating"] == 5
        assert result["data"]["createReview"]["title"] == "Excellent!"

    def test_create_review_unauthenticated(self, client: TestClient, sample_book: Book):
        """Test creating a review without authentication."""
        query = """
        mutation($bookId: Int!, $input: ReviewInput!) {
            createReview(bookId: $bookId, input: $input) {
                id
            }
        }
        """
        variables = {
            "bookId": sample_book.id,
            "input": {
                "rating": 5,
            }
        }
        result = graphql_query(client, query, variables=variables)

        assert "errors" in result

    def test_update_own_review(
        self, client: TestClient, sample_user: User, sample_book: Book, db_session: Session
    ):
        """Test updating own review."""
        # Create a review
        review = Review(
            book_id=sample_book.id,
            user_id=sample_user.id,
            rating=3,
            title="Good",
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        token = get_auth_token(sample_user)

        query = """
        mutation($id: Int!, $input: ReviewUpdateInput!) {
            updateReview(id: $id, input: $input) {
                id
                rating
                title
            }
        }
        """
        variables = {
            "id": review.id,
            "input": {
                "rating": 5,
                "title": "Actually great!",
            }
        }
        result = graphql_query(client, query, variables=variables, token=token)

        assert "errors" not in result
        assert result["data"]["updateReview"]["rating"] == 5

    def test_delete_own_review(
        self, client: TestClient, sample_user: User, sample_book: Book, db_session: Session
    ):
        """Test deleting own review."""
        # Create a review
        review = Review(
            book_id=sample_book.id,
            user_id=sample_user.id,
            rating=4,
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        token = get_auth_token(sample_user)

        query = """
        mutation($id: Int!) {
            deleteReview(id: $id)
        }
        """
        result = graphql_query(client, query, variables={"id": review.id}, token=token)

        assert "errors" not in result
        assert result["data"]["deleteReview"] is True
