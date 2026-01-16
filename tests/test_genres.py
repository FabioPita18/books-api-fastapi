"""
Tests for Genres API Endpoints

Tests for /api/v1/genres endpoints.
"""

from fastapi import status


class TestListGenres:
    """Tests for GET /api/v1/genres/ endpoint."""

    def test_list_genres_empty(self, client):
        """Test listing genres when database is empty."""
        response = client.get("/api/v1/genres/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_genres_with_data(self, client, sample_genre):
        """Test listing genres returns expected data."""
        response = client.get("/api/v1/genres/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Science Fiction"


class TestGetGenre:
    """Tests for GET /api/v1/genres/{genre_id} endpoint."""

    def test_get_genre_success(self, client, sample_genre):
        """Test getting a genre by ID."""
        response = client.get(f"/api/v1/genres/{sample_genre.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_genre.id
        assert data["name"] == "Science Fiction"

    def test_get_genre_not_found(self, client):
        """Test getting a non-existent genre returns 404."""
        response = client.get("/api/v1/genres/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateGenre:
    """Tests for POST /api/v1/genres/ endpoint."""

    def test_create_genre_minimal(self, client):
        """Test creating a genre with only required fields."""
        genre_data = {"name": "Mystery"}

        response = client.post("/api/v1/genres/", json=genre_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Mystery"
        assert data["description"] is None

    def test_create_genre_full(self, client):
        """Test creating a genre with all fields."""
        genre_data = {
            "name": "Horror",
            "description": "Fiction intended to frighten.",
        }

        response = client.post("/api/v1/genres/", json=genre_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Horror"
        assert data["description"] == "Fiction intended to frighten."

    def test_create_genre_duplicate_name(self, client, sample_genre):
        """Test that duplicate genre name is rejected."""
        genre_data = {"name": "Science Fiction"}  # Already exists

        response = client.post("/api/v1/genres/", json=genre_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_genre_empty_name(self, client):
        """Test that empty name is rejected."""
        genre_data = {"name": "   "}

        response = client.post("/api/v1/genres/", json=genre_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateGenre:
    """Tests for PUT /api/v1/genres/{genre_id} endpoint."""

    def test_update_genre_description(self, client, sample_genre):
        """Test updating genre description."""
        update_data = {"description": "Updated description"}

        response = client.put(
            f"/api/v1/genres/{sample_genre.id}",
            json=update_data,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["name"] == "Science Fiction"  # Unchanged

    def test_update_genre_not_found(self, client):
        """Test updating a non-existent genre returns 404."""
        response = client.put(
            "/api/v1/genres/99999",
            json={"name": "Updated"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteGenre:
    """Tests for DELETE /api/v1/genres/{genre_id} endpoint."""

    def test_delete_genre_success(self, client, sample_genre):
        """Test deleting a genre successfully."""
        response = client.delete(f"/api/v1/genres/{sample_genre.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify genre is deleted
        get_response = client.get(f"/api/v1/genres/{sample_genre.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_genre_not_found(self, client):
        """Test deleting a non-existent genre returns 404."""
        response = client.delete("/api/v1/genres/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
