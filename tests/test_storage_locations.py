"""
Tests für StorageLocations CRUD Endpoints.
"""
import pytest
from uuid import uuid4


class TestGetStorageLocations:
    """Tests für GET /storage-locations/"""
    
    def test_get_all_empty(self, client, admin_token):
        """Leere Liste wenn keine Lagerorte existieren."""
        response = client.get(
            "/storage-locations/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_all_with_data(self, client, admin_token, storage_location):
        """Liste mit Lagerorten."""
        response = client.get(
            "/storage-locations/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == storage_location.name
        assert data[0]["department"]["id"] == str(storage_location.department_id)
    
    def test_get_filtered_by_name(self, client, admin_token, storage_location):
        """Filter nach Name funktioniert."""
        response = client.get(
            f"/storage-locations/?name={storage_location.name[:4]}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_get_filtered_by_name_no_match(self, client, admin_token, storage_location):
        """Filter nach Name ohne Treffer."""
        response = client.get(
            "/storage-locations/?name=gibtsgarantiertnicht",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_filtered_by_department(self, client, admin_token, storage_location):
        """Filter nach Department funktioniert."""
        response = client.get(
            f"/storage-locations/?department_id={storage_location.department_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_get_without_auth(self, client):
        """Ohne Token → 401."""
        response = client.get("/storage-locations/")
        assert response.status_code == 401


class TestGetStorageLocationById:
    """Tests für GET /storage-locations/{id}"""
    
    def test_get_by_id_success(self, client, admin_token, storage_location):
        """Einzelnen Lagerort abrufen."""
        response = client.get(
            f"/storage-locations/{storage_location.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == storage_location.name
        assert data["department"]["id"] == str(storage_location.department_id)
    
    def test_get_by_id_not_found(self, client, admin_token):
        """Nicht existierender Lagerort → 404."""
        response = client.get(
            f"/storage-locations/{uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_get_inactive_not_found(self, client, admin_token, storage_location, db):
        """Inaktiver Lagerort wird nicht gefunden."""
        storage_location.is_active = False
        db.commit()
        
        response = client.get(
            f"/storage-locations/{storage_location.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestCreateStorageLocation:
    """Tests für POST /storage-locations/"""
    
    def test_create_success(self, client, admin_token, department):
        """Lagerort erstellen - Happy Path."""
        response = client.post(
            "/storage-locations/",
            json={
                "name": "Neuer Lagerort",
                "department_id": str(department.id)
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Neuer Lagerort"
        assert data["department"]["id"] == str(department.id)
        assert data["is_active"] == True
    
    def test_create_department_not_found(self, client, admin_token):
        """Department existiert nicht → 404."""
        response = client.post(
            "/storage-locations/",
            json={
                "name": "Test Lagerort",
                "department_id": str(uuid4())
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Abteilung" in response.json()["detail"]
    
    def test_create_without_auth(self, client, department):
        """Ohne Token → 401."""
        response = client.post(
            "/storage-locations/",
            json={
                "name": "Test",
                "department_id": str(department.id)
            }
        )
        assert response.status_code == 401
    
    def test_create_not_admin(self, client, user_token, department):
        """Nicht-Admin → 403."""
        response = client.post(
            "/storage-locations/",
            json={
                "name": "Test",
                "department_id": str(department.id)
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestUpdateStorageLocation:
    """Tests für PATCH /storage-locations/{id}"""
    
    def test_update_name(self, client, admin_token, storage_location):
        """Name ändern."""
        response = client.patch(
            f"/storage-locations/{storage_location.id}",
            json={"name": "Neuer Name"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Neuer Name"
    
    def test_update_department(self, client, admin_token, storage_location, db):
        """Department ändern."""
        from app.models import Department
        
        # Neues Department erstellen
        new_dept = Department(name="Neues Department")
        db.add(new_dept)
        db.commit()
        db.refresh(new_dept)
        
        response = client.patch(
            f"/storage-locations/{storage_location.id}",
            json={"department_id": str(new_dept.id)},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["department"]["id"] == str(new_dept.id)
    
    def test_update_department_not_found(self, client, admin_token, storage_location):
        """Neues Department existiert nicht → 404."""
        response = client.patch(
            f"/storage-locations/{storage_location.id}",
            json={"department_id": str(uuid4())},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "Abteilung" in response.json()["detail"]
    
    def test_update_not_found(self, client, admin_token):
        """Lagerort existiert nicht → 404."""
        response = client.patch(
            f"/storage-locations/{uuid4()}",
            json={"name": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_update_not_admin(self, client, user_token, storage_location):
        """Nicht-Admin → 403."""
        response = client.patch(
            f"/storage-locations/{storage_location.id}",
            json={"name": "Test"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestDeleteStorageLocation:
    """Tests für DELETE /storage-locations/{id}"""
    
    def test_delete_success(self, client, admin_token, storage_location, db):
        """Soft Delete funktioniert."""
        response = client.delete(
            f"/storage-locations/{storage_location.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Prüfen dass is_active = False
        db.refresh(storage_location)
        assert storage_location.is_active == False
    
    def test_delete_not_found(self, client, admin_token):
        """Nicht existierender Lagerort → 404."""
        response = client.delete(
            f"/storage-locations/{uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_delete_not_admin(self, client, user_token, storage_location):
        """Nicht-Admin → 403."""
        response = client.delete(
            f"/storage-locations/{storage_location.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403