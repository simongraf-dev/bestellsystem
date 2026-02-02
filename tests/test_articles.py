"""
Tests für Articles Endpoints.

Testet:
- GET /articles/
- GET /articles/{id}
- POST /articles/
- PATCH /articles/{id}
- DELETE /articles/{id}
"""
import pytest
from uuid import uuid4

from app.models import Article
from tests.conftest import auth_header


class TestGetArticles:
    """Tests für GET /articles/"""
    
    def test_get_articles_empty(self, client, admin_token):
        """Leere Liste wenn keine Artikel existieren"""
        response = client.get(
            "/articles/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        # Könnte leer sein oder fixture-artikel enthalten
        assert isinstance(response.json(), list)
    
    def test_get_articles_with_data(self, client, admin_token, article):
        """Liste mit Artikeln"""
        response = client.get(
            "/articles/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(a["name"] == "Karotten" for a in data)
    
    def test_get_articles_search(self, client, admin_token, article):
        """Suche nach Namen"""
        response = client.get(
            "/articles/?name=Karott",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all("Karott" in a["name"] for a in data)
    
    def test_get_articles_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/articles/")
        assert response.status_code == 401


class TestGetArticleById:
    """Tests für GET /articles/{id}"""
    
    def test_get_article_success(self, client, admin_token, article):
        """Einzelnen Artikel abrufen"""
        response = client.get(
            f"/articles/{article.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Karotten"
        assert data["unit"] == "kg"
    
    def test_get_article_not_found(self, client, admin_token):
        """Artikel nicht gefunden → 404"""
        response = client.get(
            f"/articles/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestCreateArticle:
    """Tests für POST /articles/"""
    
    def test_create_article_success(self, client, admin_token, article_group):
        """Admin kann Artikel erstellen"""
        response = client.post(
            "/articles/",
            json={
                "name": "Tomaten",
                "unit": "kg",
                "article_group_id": str(article_group.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Tomaten"
        assert data["unit"] == "kg"
        assert data["is_active"] == True
    
    def test_create_article_with_notes(self, client, admin_token, article_group):
        """Artikel mit Notizen erstellen"""
        response = client.post(
            "/articles/",
            json={
                "name": "Bio-Äpfel",
                "unit": "Stück",
                "article_group_id": str(article_group.id),
                "notes": "Nur regionale Ware"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Nur regionale Ware"
    
    def test_create_article_invalid_group(self, client, admin_token):
        """Ungültige Artikelgruppe → Fehler"""
        response = client.post(
            "/articles/",
            json={
                "name": "Test",
                "unit": "kg",
                "article_group_id": str(uuid4())
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code in [400, 404]
    
    def test_create_article_not_admin(self, client, bedarfsmelder_token, article_group):
        """Nicht-Admin kann keine Artikel erstellen → 403"""
        response = client.post(
            "/articles/",
            json={
                "name": "Versuch",
                "unit": "kg",
                "article_group_id": str(article_group.id)
            },
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403


class TestUpdateArticle:
    """Tests für PATCH /articles/{id}"""
    
    def test_update_article_success(self, client, admin_token, article):
        """Admin kann Artikel bearbeiten"""
        response = client.patch(
            f"/articles/{article.id}",
            json={"name": "Bio-Karotten"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bio-Karotten"
    
    def test_update_article_unit(self, client, admin_token, article):
        """Einheit ändern"""
        response = client.patch(
            f"/articles/{article.id}",
            json={"unit": "Bund"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["unit"] == "Bund"
    
    def test_update_article_not_found(self, client, admin_token):
        """Artikel nicht gefunden → 404"""
        response = client.patch(
            f"/articles/{uuid4()}",
            json={"name": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestDeleteArticle:
    """Tests für DELETE /articles/{id}"""
    
    def test_delete_article_success(self, client, admin_token, db, article_group):
        """Admin kann Artikel löschen (Soft Delete)"""
        # Neuen Artikel zum Löschen erstellen
        art = Article(
            id=uuid4(),
            name="Zum Löschen",
            unit="kg",
            article_group_id=article_group.id,
            is_active=True
        )
        db.add(art)
        db.commit()
        
        response = client.delete(
            f"/articles/{art.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen ob deaktiviert
        db.refresh(art)
        assert art.is_active == False
    
    def test_delete_article_not_found(self, client, admin_token):
        """Artikel nicht gefunden → 404"""
        response = client.delete(
            f"/articles/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404