"""
Tests für Departments Endpoints.

Testet:
- GET /departments/
- GET /departments/{id}
- POST /departments/
- PATCH /departments/{id}
- DELETE /departments/{id}
"""
import pytest
from uuid import uuid4

from app.models import Department
from tests.conftest import auth_header


class TestGetDepartments:
    """Tests für GET /departments/"""
    
    def test_get_departments_with_data(self, client, admin_token, department):
        """Liste mit Abteilungen"""
        response = client.get(
            "/departments/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(d["name"] == "Test-Küche" for d in data)
    
    def test_get_departments_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/departments/")
        assert response.status_code == 401


class TestGetDepartmentById:
    """Tests für GET /departments/{id}"""
    
    def test_get_department_success(self, client, admin_token, department):
        """Einzelne Abteilung abrufen"""
        response = client.get(
            f"/departments/{department.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test-Küche"
    
    def test_get_department_not_found(self, client, admin_token):
        """Abteilung nicht gefunden → 404"""
        response = client.get(
            f"/departments/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestCreateDepartment:
    """Tests für POST /departments/"""
    
    def test_create_department_success(self, client, admin_token):
        """Admin kann Abteilung erstellen"""
        response = client.post(
            "/departments/",
            json={"name": "Service"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Service"
        assert data["is_active"] == True
        assert data["parent"] is None
    
    def test_create_department_with_parent(self, client, admin_token, department):
        """Abteilung mit Parent erstellen (Hierarchie)"""
        response = client.post(
            "/departments/",
            json={
                "name": "Kalt-Küche",
                "parent_id": str(department.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Kalt-Küche"
        assert data["parent"]["name"] == "Test-Küche"
    
    def test_create_department_invalid_parent(self, client, admin_token):
        """Ungültiger Parent → Fehler"""
        response = client.post(
            "/departments/",
            json={
                "name": "Test",
                "parent_id": str(uuid4())
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code in [400, 404]
    
    def test_create_department_not_admin(self, client, bedarfsmelder_token):
        """Nicht-Admin kann keine Abteilung erstellen → 403"""
        response = client.post(
            "/departments/",
            json={"name": "Versuch"},
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403


class TestUpdateDepartment:
    """Tests für PATCH /departments/{id}"""
    
    def test_update_department_success(self, client, admin_token, db):
        """Admin kann Abteilung bearbeiten"""
        # Extra Department erstellen
        dept = Department(id=uuid4(), name="Alt", is_active=True)
        db.add(dept)
        db.commit()
        
        response = client.patch(
            f"/departments/{dept.id}",
            json={"name": "Neu"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Neu"
    
    def test_update_department_not_found(self, client, admin_token):
        """Abteilung nicht gefunden → 404"""
        response = client.patch(
            f"/departments/{uuid4()}",
            json={"name": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestDeleteDepartment:
    """Tests für DELETE /departments/{id}"""
    
    def test_delete_department_success(self, client, admin_token, db):
        """Admin kann Abteilung löschen (Soft Delete)"""
        # Department ohne Children
        dept = Department(id=uuid4(), name="Zum Löschen", is_active=True)
        db.add(dept)
        db.commit()
        
        response = client.delete(
            f"/departments/{dept.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen ob deaktiviert
        db.refresh(dept)
        assert dept.is_active == False
    
    def test_delete_department_with_children(self, client, admin_token, db):
        """Abteilung mit Children kann nicht gelöscht werden"""
        # Parent erstellen
        parent = Department(id=uuid4(), name="Parent", is_active=True)
        db.add(parent)
        db.commit()
        
        # Child erstellen
        child = Department(id=uuid4(), name="Child", parent_id=parent.id, is_active=True)
        db.add(child)
        db.commit()
        
        # Parent löschen sollte fehlschlagen
        response = client.delete(
            f"/departments/{parent.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_delete_department_not_found(self, client, admin_token):
        """Abteilung nicht gefunden → 404"""
        response = client.delete(
            f"/departments/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404