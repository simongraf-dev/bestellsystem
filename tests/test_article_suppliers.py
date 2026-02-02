"""
Tests für ArticleSuppliers Endpoints.

Testet:
- GET /article-suppliers/
- POST /article-suppliers/
- DELETE /article-suppliers/{id}
"""
import pytest
from uuid import uuid4
from decimal import Decimal

from app.models import ArticleSupplier
from tests.conftest import auth_header


class TestGetArticleSuppliers:
    """Tests für GET /article-suppliers/"""
    
    def test_get_article_suppliers_empty(self, client, admin_token):
        """Leere Liste"""
        response = client.get(
            "/article-suppliers/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_article_suppliers_with_data(self, client, admin_token, db, article, supplier):
        """Liste mit Verknüpfungen"""
        # Verknüpfung erstellen
        link = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        response = client.get(
            "/article-suppliers/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_get_article_suppliers_filter_article(self, client, admin_token, db, article, supplier):
        """Filter nach Artikel"""
        link = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        response = client.get(
            f"/article-suppliers/?article_id={article.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(as_["article"]["id"] == str(article.id) for as_ in data)
    
    def test_get_article_suppliers_filter_supplier(self, client, admin_token, db, article, supplier):
        """Filter nach Lieferant"""
        link = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        response = client.get(
            f"/article-suppliers/?supplier_id={supplier.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_get_article_suppliers_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/article-suppliers/")
        assert response.status_code == 401


class TestCreateArticleSupplier:
    """Tests für POST /article-suppliers/"""
    
    def test_create_article_supplier_success(self, client, admin_token, article, supplier):
        """Verknüpfung erstellen"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(supplier.id),
                "price": 3.50,
                "unit": "kg",
                "article_number_supplier": "ART-001"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert float(data["price"]) == 3.50
        assert data["unit"] == "kg"
        assert data["article_number_supplier"] == "ART-001"
    
    def test_create_article_supplier_minimal(self, client, admin_token, article, supplier):
        """Verknüpfung mit minimalen Daten"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(supplier.id),
                "unit": "Stück"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["unit"] == "Stück"
    
    def test_create_article_supplier_duplicate(self, client, admin_token, db, article, supplier):
        """Doppelte Verknüpfung → Fehler"""
        # Erst erstellen
        link = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        # Nochmal versuchen
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(supplier.id),
                "unit": "kg"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_create_article_supplier_invalid_article(self, client, admin_token, supplier):
        """Ungültiger Artikel → Fehler"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(uuid4()),
                "supplier_id": str(supplier.id),
                "unit": "kg"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code in [400, 404]
    
    def test_create_article_supplier_invalid_supplier(self, client, admin_token, article):
        """Ungültiger Lieferant → Fehler"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(uuid4()),
                "unit": "kg"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code in [400, 404]
    
    def test_create_article_supplier_negative_price(self, client, admin_token, article, supplier):
        """Negativer Preis → Validierungsfehler"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(supplier.id),
                "price": -5.0,
                "unit": "kg"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 422
    
    def test_create_article_supplier_not_admin(self, client, bedarfsmelder_token, article, supplier):
        """Nicht-Admin → 403"""
        response = client.post(
            "/article-suppliers/",
            json={
                "article_id": str(article.id),
                "supplier_id": str(supplier.id),
                "unit": "kg"
            },
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403


class TestDeleteArticleSupplier:
    """Tests für DELETE /article-suppliers/{id}"""
    
    def test_delete_article_supplier_success(self, client, admin_token, db, article, supplier):
        """Verknüpfung löschen"""
        link = ArticleSupplier(
            id=uuid4(),
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        response = client.delete(
            f"/article-suppliers/{link.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen dass gelöscht
        deleted = db.query(ArticleSupplier).filter(ArticleSupplier.id == link.id).first()
        assert deleted is None
    
    def test_delete_article_supplier_not_found(self, client, admin_token):
        """Verknüpfung nicht gefunden → 404"""
        response = client.delete(
            f"/article-suppliers/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_delete_article_supplier_not_admin(self, client, bedarfsmelder_token, db, article, supplier):
        """Nicht-Admin → 403"""
        link = ArticleSupplier(
            id=uuid4(),
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(link)
        db.commit()
        
        response = client.delete(
            f"/article-suppliers/{link.id}",
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403