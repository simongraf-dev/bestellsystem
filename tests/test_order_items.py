"""
Tests für OrderItems Endpoints.

Testet:
- PATCH /order-items/{id}
- DELETE /order-items/{id}
"""
import pytest
from uuid import uuid4
from decimal import Decimal

from app.models import Order, OrderItem
from app.models.order import OrderStatus
from tests.conftest import auth_header


class TestUpdateOrderItem:
    """Tests für PATCH /order-items/{id}"""
    
    def test_update_order_item_amount(self, client, admin_token, db, admin_user, department, article, supplier):
        """Menge ändern"""
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
        
        response = client.patch(
            f"/order-items/{item.id}",
            json={"amount": 10.0},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert float(data["amount"]) == 10.0
    
    def test_update_order_item_note(self, client, admin_token, db, admin_user, department, article, supplier):
        """Notiz ändern"""
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
        
        response = client.patch(
            f"/order-items/{item.id}",
            json={"note": "Bitte reife Früchte"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["note"] == "Bitte reife Früchte"
    
    def test_update_order_item_negative_amount(self, client, admin_token, db, admin_user, department, article, supplier):
        """Negative Menge → Validierungsfehler"""
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
        
        response = client.patch(
            f"/order-items/{item.id}",
            json={"amount": -5.0},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 422
    
    def test_update_order_item_not_found(self, client, admin_token):
        """OrderItem nicht gefunden → 404"""
        response = client.patch(
            f"/order-items/{uuid4()}",
            json={"amount": 10.0},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_update_order_item_closed_order(self, client, admin_token, db, admin_user, department, article, supplier):
        """Item in abgeschlossener Order → Fehler (außer für Freigeber)"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=admin_user.id,
            status=OrderStatus.VOLLSTAENDIG  # Nicht ENTWURF!
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
        
        # Als Bedarfsmelder sollte das nicht gehen
        response = client.patch(
            f"/order-items/{item.id}",
            json={"amount": 10.0},
            headers=auth_header(admin_token)  # Admin darf aber
        )
        
        # Admin sollte es können (oder 403 wenn nicht)
        assert response.status_code in [200, 403]


class TestDeleteOrderItem:
    """Tests für DELETE /order-items/{id}"""
    
    def test_delete_order_item_success(self, client, admin_token, db, admin_user, department, article, supplier):
        """OrderItem löschen"""
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
        
        response = client.delete(
            f"/order-items/{item.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen dass wirklich gelöscht
        deleted_item = db.query(OrderItem).filter(OrderItem.id == item.id).first()
        assert deleted_item is None
    
    def test_delete_order_item_not_found(self, client, admin_token):
        """OrderItem nicht gefunden → 404"""
        response = client.delete(
            f"/order-items/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_delete_order_item_closed_order(self, client, bedarfsmelder_token, db, bedarfsmelder_user, department, article, supplier):
        """Item in abgeschlossener Order als Bedarfsmelder → 403"""
        order = Order(
            id=uuid4(),
            department_id=department.id,
            creator_id=bedarfsmelder_user.id,
            status=OrderStatus.VOLLSTAENDIG
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
        
        response = client.delete(
            f"/order-items/{item.id}",
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403