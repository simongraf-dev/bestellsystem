"""
Tests für ShippingGroup Endpoints.

Testet:
- GET /shipping-groups/
- GET /shipping-groups/{id}
- POST /shipping-groups/{id}/freigeben
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date, timedelta

from app.models import Order, OrderItem, ShippingGroup, ApproverSupplier
from app.models.order import OrderStatus
from app.models.shipping_group import ShippingGroupStatus
from tests.conftest import auth_header


class TestGetShippingGroups:
    """Tests für GET /shipping-groups/"""
    
    def test_get_shipping_groups_empty(self, client, admin_token):
        """Leere Liste wenn keine ShippingGroups existieren"""
        response = client.get(
            "/shipping-groups/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_shipping_groups_admin_sees_all(self, client, admin_token, db, supplier):
        """Admin sieht alle ShippingGroups"""
        # ShippingGroup erstellen
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            delivery_date=date.today() + timedelta(days=1),
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.get(
            "/shipping-groups/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "OFFEN"
    
    def test_get_shipping_groups_freigeber_only_own(self, client, freigeber_token, db, freigeber_user, supplier):
        """Freigeber sieht nur ShippingGroups seiner Lieferanten"""
        # ShippingGroup ohne Berechtigung
        sg1 = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg1)
        db.commit()
        
        # Ohne ApproverSupplier → sollte leer sein
        response = client.get(
            "/shipping-groups/",
            headers=auth_header(freigeber_token)
        )
        
        assert response.status_code == 200
        assert response.json() == []
        
        # Jetzt ApproverSupplier erstellen
        approver = ApproverSupplier(
            user_id=freigeber_user.id,
            supplier_id=supplier.id
        )
        db.add(approver)
        db.commit()
        
        # Jetzt sollte die ShippingGroup sichtbar sein
        response = client.get(
            "/shipping-groups/",
            headers=auth_header(freigeber_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_get_shipping_groups_filter_status(self, client, admin_token, db, supplier):
        """Filter nach Status funktioniert"""
        # Zwei ShippingGroups mit unterschiedlichem Status
        sg_offen = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.OFFEN
        )
        sg_versendet = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.VERSENDET
        )
        db.add_all([sg_offen, sg_versendet])
        db.commit()
        
        # Nur OFFEN
        response = client.get(
            "/shipping-groups/?status=OFFEN",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "OFFEN"
    
    def test_get_shipping_groups_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/shipping-groups/")
        assert response.status_code == 401


class TestGetShippingGroupDetail:
    """Tests für GET /shipping-groups/{id}"""
    
    def test_get_shipping_group_success(self, client, admin_token, db, supplier):
        """Erfolgreicher Abruf einer ShippingGroup"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            delivery_date=date.today() + timedelta(days=2),
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.get(
            f"/shipping-groups/{sg.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["supplier"]["name"] == "Test Gemüsehändler"
        assert data["status"] == "OFFEN"
    
    def test_get_shipping_group_not_found(self, client, admin_token):
        """ShippingGroup nicht gefunden → 404"""
        response = client.get(
            f"/shipping-groups/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_get_shipping_group_no_permission(self, client, freigeber_token, db, supplier):
        """Freigeber ohne Berechtigung → 403"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.get(
            f"/shipping-groups/{sg.id}",
            headers=auth_header(freigeber_token)
        )
        
        assert response.status_code == 403


class TestFreigebenShippingGroup:
    """Tests für POST /shipping-groups/{id}/freigeben"""
    
    def test_freigeben_success(self, client, admin_token, db, supplier):
        """Erfolgreiche Freigabe: OFFEN → VERSENDET"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            delivery_date=date.today() + timedelta(days=1),
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "VERSENDET"
    
    def test_freigeben_already_versendet(self, client, admin_token, db, supplier):
        """Bereits versendet → Fehler"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.VERSENDET
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_freigeben_past_delivery_date(self, client, admin_token, db, supplier):
        """Lieferdatum in Vergangenheit → Fehler"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            delivery_date=date.today() - timedelta(days=1),  # Gestern!
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_freigeben_not_found(self, client, admin_token):
        """ShippingGroup nicht gefunden → 404"""
        response = client.post(
            f"/shipping-groups/{uuid4()}/freigeben",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_freigeben_no_permission(self, client, freigeber_token, db, supplier):
        """Freigeber ohne ApproverSupplier → 403"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(freigeber_token)
        )
        
        assert response.status_code == 403
    
    def test_freigeben_with_permission(self, client, freigeber_token, db, freigeber_user, supplier):
        """Freigeber MIT ApproverSupplier → Erfolg"""
        # Berechtigung erstellen
        approver = ApproverSupplier(
            user_id=freigeber_user.id,
            supplier_id=supplier.id
        )
        db.add(approver)
        
        # ShippingGroup erstellen
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            delivery_date=date.today() + timedelta(days=1),
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(freigeber_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "VERSENDET"
    
    def test_freigeben_bedarfsmelder_not_allowed(self, client, bedarfsmelder_token, db, supplier):
        """Bedarfsmelder kann nicht freigeben → 403"""
        sg = ShippingGroup(
            id=uuid4(),
            supplier_id=supplier.id,
            status=ShippingGroupStatus.OFFEN
        )
        db.add(sg)
        db.commit()
        
        response = client.post(
            f"/shipping-groups/{sg.id}/freigeben",
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403