"""
Tests für ArticleStorageLocations CRUD Endpoints.
"""
import pytest
from uuid import uuid4


class TestGetArticleStorageLocations:
    """Tests für GET /article-storage-locations/"""
    
    def test_get_all_empty(self, client, admin_token):
        """Leere Liste wenn keine Verknüpfungen existieren."""
        response = client.get(
            "/article-storage-locations/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_all_with_data(self, client, admin_token, article_storage_location):
        """Liste mit Verknüpfungen."""
        response = client.get(
            "/article-storage-locations/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["article"]["id"] == str(article_storage_location.article_id)
        assert data[0]["storage_location"]["id"] == str(article_storage_location.storage_location_id)
    
    def test_get_filtered_by_article(self, client, admin_token, article_storage_location):
        """Filter nach Artikel funktioniert."""
        response = client.get(
            f"/article-storage-locations/?article_id={article_storage_location.article_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_get_filtered_by_storage_location(self, client, admin_token, article_storage_location):
        """Filter nach Lagerort funktioniert."""
        response = client.get(
            f"/article-storage-locations/?storage_location_id={article_storage_location.storage_location_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_get_filtered_no_match(self, client, admin_token, article_storage_location):
        """Filter ohne Treffer."""
        response = client.get(
            f"/article-storage-locations/?article_id={uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_without_auth(self, client):
        """Ohne Token → 401."""
        response = client.get("/article-storage-locations/")
        assert response.status_code == 401


class TestCreateArticleStorageLocation:
    """Tests für POST /article-storage-locations/"""
    
    def test_create_success(self, client, admin_token, article, storage_location):
        """Verknüpfung erstellen - Happy Path."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(storage_location.id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["article"]["id"] == str(article.id)
        assert data["storage_location"]["id"] == str(storage_location.id)
    
    def test_create_duplicate(self, client, admin_token, article_storage_location):
        """Duplikat → 400."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article_storage_location.article_id),
                "storage_location_id": str(article_storage_location.storage_location_id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        assert "existiert bereits" in response.json()["detail"]
    
    def test_create_article_not_found(self, client, admin_token, storage_location):
        """Artikel existiert nicht → 404."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(uuid4()),
                "storage_location_id": str(storage_location.id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Artikel" in response.json()["detail"]
    
    def test_create_storage_location_not_found(self, client, admin_token, article):
        """Lagerort existiert nicht → 404."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(uuid4())
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Lagerort" in response.json()["detail"]
    
    def test_create_inactive_article(self, client, admin_token, article, storage_location, db):
        """Inaktiver Artikel → 404."""
        article.is_active = False
        db.commit()
        
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(storage_location.id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Artikel" in response.json()["detail"]
    
    def test_create_inactive_storage_location(self, client, admin_token, article, storage_location, db):
        """Inaktiver Lagerort → 404."""
        storage_location.is_active = False
        db.commit()
        
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(storage_location.id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Lagerort" in response.json()["detail"]
    
    def test_create_without_auth(self, client, article, storage_location):
        """Ohne Token → 401."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(storage_location.id)
            }
        )
        assert response.status_code == 401
    
    def test_create_not_admin(self, client, user_token, article, storage_location):
        """Nicht-Admin → 403."""
        response = client.post(
            "/article-storage-locations/",
            json={
                "article_id": str(article.id),
                "storage_location_id": str(storage_location.id)
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestDeleteArticleStorageLocation:
    """Tests für DELETE /article-storage-locations/"""
    
    def test_delete_success(self, client, admin_token, article_storage_location, db):
        """Löschen funktioniert."""
        article_id = article_storage_location.article_id
        storage_location_id = article_storage_location.storage_location_id
        
        response = client.delete(
            f"/article-storage-locations/?article_id={article_id}&storage_location_id={storage_location_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Prüfen dass wirklich gelöscht
        from app.models import ArticleStorageLocation
        link = db.query(ArticleStorageLocation).filter(
            ArticleStorageLocation.article_id == article_id,
            ArticleStorageLocation.storage_location_id == storage_location_id
        ).first()
        assert link is None
    
    def test_delete_not_found(self, client, admin_token):
        """Nicht existierende Verknüpfung → 404."""
        response = client.delete(
            f"/article-storage-locations/?article_id={uuid4()}&storage_location_id={uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_delete_not_admin(self, client, user_token, article_storage_location):
        """Nicht-Admin → 403."""
        response = client.delete(
            f"/article-storage-locations/?article_id={article_storage_location.article_id}&storage_location_id={article_storage_location.storage_location_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403