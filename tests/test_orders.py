"""
Tests für Order Endpoints.

Testet:
- GET /orders/
- POST /orders/
- PATCH /orders/{id}
- POST /orders/{id}/abschliessen
- POST /orders/{id}/items
"""
import pytest
from uuid import uuid4
from decimal import Decimal

from app.models import Order, OrderItem, ArticleSupplier
from app.models.order import OrderStatus
from tests.conftest import auth_header


class TestGetOrders:
    """Tests für GET /orders/"""
    
    def test_get_orders_empty(self, client, admin_token):
        """Leere Liste wenn keine Orders existieren"""
        response = client.get(
            "/orders/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_orders_with_data(self, client, admin_token, db, admin_user, department):
        """Liste mit Orders"""
        # Order erstellen
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.ENTWURF
        )
        db.add(order)
        db.commit()
        
        response = client.get(
            "/orders/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "ENTWURF"
    
    def test_get_orders_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/orders/")
        assert response.status_code == 401


class TestCreateOrder:
    """Tests für POST /orders/"""
    
    def test_create_order_success(self, client, admin_token, db, article, supplier):
        """Erfolgreiche Order-Erstellung"""
        # Artikel-Lieferant Verknüpfung erstellen
        article_supplier = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(article_supplier)
        db.commit()
        
        response = client.post(
            "/orders/",
            json={
                "items": [
                    {"article_id": str(article.id), "amount": 5.0}
                ]
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ENTWURF"
        assert len(data["items"]) == 1
        assert float(data["items"][0]["amount"]) == 5.0
    
    def test_create_order_with_note(self, client, admin_token, db, article, supplier):
        """Order mit Notiz am Item"""
        article_supplier = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(article_supplier)
        db.commit()
        
        response = client.post(
            "/orders/",
            json={
                "items": [
                    {
                        "article_id": str(article.id),
                        "amount": 3.0,
                        "note": "Bitte reife Früchte"
                    }
                ]
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["note"] == "Bitte reife Früchte"
    
    def test_create_order_empty_items(self, client, admin_token):
        """Leere Items-Liste → Fehler"""
        response = client.post(
            "/orders/",
            json={"items": []},
            headers=auth_header(admin_token)
        )
        
        # Sollte entweder 400 oder 422 sein
        assert response.status_code in [400, 422]
    
    def test_create_order_invalid_article(self, client, admin_token):
        """Ungültiger Artikel → 404"""
        response = client.post(
            "/orders/",
            json={
                "items": [
                    {"article_id": str(uuid4()), "amount": 5.0}
                ]
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_create_order_negative_amount(self, client, admin_token, article):
        """Negative Menge → Validierungsfehler"""
        response = client.post(
            "/orders/",
            json={
                "items": [
                    {"article_id": str(article.id), "amount": -5.0}
                ]
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_create_order_without_auth(self, client, article):
        """Ohne Login → 401"""
        response = client.post(
            "/orders/",
            json={
                "items": [
                    {"article_id": str(article.id), "amount": 5.0}
                ]
            }
        )
        
        assert response.status_code == 401


class TestUpdateOrder:
    """Tests für PATCH /orders/{id}"""
    
    def test_update_order_success(self, client, admin_token, db, admin_user, department):
        """Erfolgreiche Order-Aktualisierung"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.ENTWURF
        )
        db.add(order)
        db.commit()
        
        response = client.patch(
            f"/orders/{order.id}",
            json={
                "delivery_notes": "Bitte vor 10 Uhr liefern",
                "additional_articles": "Falls keine Karotten, dann Pastinaken"
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["delivery_notes"] == "Bitte vor 10 Uhr liefern"
        assert data["additional_articles"] == "Falls keine Karotten, dann Pastinaken"
    
    def test_update_order_not_entwurf(self, client, admin_token, db, admin_user, department):
        """Update nur bei ENTWURF möglich"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.VOLLSTAENDIG  # Nicht ENTWURF!
        )
        db.add(order)
        db.commit()
        
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_update_order_not_found(self, client, admin_token):
        """Order nicht gefunden → 404"""
        response = client.patch(
            f"/orders/{uuid4()}",
            json={"delivery_notes": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestCloseOrder:
    """Tests für POST /orders/{id}/abschliessen"""
    
    def test_close_order_success(self, client, admin_token, db, admin_user, department, article, supplier):
        """Erfolgreicher Abschluss: ENTWURF → VOLLSTAENDIG"""
        # Order mit Item erstellen
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.ENTWURF
        )
        db.add(order)
        db.flush()
        
        item = OrderItem(
            id=uuid4(),
            order_id=order.id,
            article_id=article.id,
            supplier_id=supplier.id,
            amount=Decimal("5.0")
        )
        db.add(item)
        db.commit()
        
        response = client.post(
            f"/orders/{order.id}/abschliessen",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "VOLLSTAENDIG"
    
    def test_close_order_empty(self, client, admin_token, db, admin_user, department):
        """Order ohne Items kann nicht abgeschlossen werden"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.ENTWURF
        )
        db.add(order)
        db.commit()
        
        response = client.post(
            f"/orders/{order.id}/abschliessen",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_close_order_already_closed(self, client, admin_token, db, admin_user, department):
        """Bereits abgeschlossene Order → Fehler"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.VOLLSTAENDIG
        )
        db.add(order)
        db.commit()
        
        response = client.post(
            f"/orders/{order.id}/abschliessen",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_close_order_not_found(self, client, admin_token):
        """Order nicht gefunden → 404"""
        response = client.post(
            f"/orders/{uuid4()}/abschliessen",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestAddItemToOrder:
    """Tests für POST /orders/{id}/items"""
    
    def test_add_item_success(self, client, admin_token, db, admin_user, department, article, supplier):
        """Erfolgreich Item hinzufügen"""
        # Artikel-Lieferant Verknüpfung
        article_supplier = ArticleSupplier(
            article_id=article.id,
            supplier_id=supplier.id,
            price=Decimal("2.50"),
            unit="kg"
        )
        db.add(article_supplier)
        
        # Order erstellen
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.ENTWURF
        )
        db.add(order)
        db.commit()
        
        response = client.post(
            f"/orders/{order.id}/items",
            json={"article_id": str(article.id), "amount": 3.0},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert float(data["items"][0]["amount"]) == 3.0
    
    def test_add_item_to_closed_order(self, client, admin_token, db, admin_user, department, article):
        """Kein Item hinzufügen zu abgeschlossener Order"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.VOLLSTAENDIG
        )
        db.add(order)
        db.commit()
        
        response = client.post(
            f"/orders/{order.id}/items",
            json={"article_id": str(article.id), "amount": 3.0},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400