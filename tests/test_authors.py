"""
Tests for Authors API Endpoints

Tests for /api/v1/authors endpoints.
"""

from fastapi import status


class TestListAuthors:
    """Tests for GET /api/v1/authors/ endpoint."""

    def test_list_authors_empty(self, client):
        """Test listing authors when database is empty."""
        response = client.get("/api/v1/authors/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_authors_with_data(self, client, sample_author):
        """Test listing authors returns expected data."""
        response = client.get("/api/v1/authors/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "George Orwell"


class TestGetAuthor:
    """Tests for GET /api/v1/authors/{author_id} endpoint."""

    def test_get_author_success(self, client, sample_author):
        """Test getting an author by ID."""
        response = client.get(f"/api/v1/authors/{sample_author.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_author.id
        assert data["name"] == "George Orwell"
        assert "created_at" in data

    def test_get_author_not_found(self, client):
        """Test getting a non-existent author returns 404."""
        response = client.get("/api/v1/authors/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateAuthor:
    """Tests for POST /api/v1/authors/ endpoint."""

    def test_create_author_minimal(self, client):
        """Test creating an author with only required fields."""
        author_data = {"name": "Jane Austen"}

        response = client.post("/api/v1/authors/", json=author_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Jane Austen"
        assert data["bio"] is None

    def test_create_author_full(self, client):
        """Test creating an author with all fields."""
        author_data = {
            "name": "Ernest Hemingway",
            "bio": "American novelist and journalist.",
        }

        response = client.post("/api/v1/authors/", json=author_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Ernest Hemingway"
        assert data["bio"] == "American novelist and journalist."

    def test_create_author_empty_name(self, client):
        """Test that empty name is rejected."""
        author_data = {"name": "   "}

        response = client.post("/api/v1/authors/", json=author_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateAuthor:
    """Tests for PUT /api/v1/authors/{author_id} endpoint."""

    def test_update_author_name(self, client, sample_author):
        """Test updating author name."""
        update_data = {"name": "Eric Arthur Blair"}

        response = client.put(
            f"/api/v1/authors/{sample_author.id}",
            json=update_data,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Eric Arthur Blair"

    def test_update_author_not_found(self, client):
        """Test updating a non-existent author returns 404."""
        response = client.put(
            "/api/v1/authors/99999",
            json={"name": "Updated"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteAuthor:
    """Tests for DELETE /api/v1/authors/{author_id} endpoint."""

    def test_delete_author_success(self, client, sample_author):
        """Test deleting an author successfully."""
        response = client.delete(f"/api/v1/authors/{sample_author.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify author is deleted
        get_response = client.get(f"/api/v1/authors/{sample_author.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_author_not_found(self, client):
        """Test deleting a non-existent author returns 404."""
        response = client.delete("/api/v1/authors/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
