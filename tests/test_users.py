"""
Tests für Users Endpoints.

Testet:
- GET /users/
- GET /users/{id}
- POST /users/
- PATCH /users/{id}
- DELETE /users/{id}
"""
import pytest
from uuid import uuid4

from app.models import User
from app.utils.security import hash_password
from tests.conftest import auth_header


class TestGetUsers:
    """Tests für GET /users/"""
    
    def test_get_users_success(self, client, admin_token, admin_user):
        """Admin kann alle User abrufen"""
        response = client.get(
            "/users/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(u["email"] == "admin@test.com" for u in data)
    
    def test_get_users_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/users/")
        assert response.status_code == 401


class TestGetUserById:
    """Tests für GET /users/{id}"""
    
    def test_get_user_success(self, client, admin_token, admin_user):
        """Einzelnen User abrufen"""
        response = client.get(
            f"/users/{admin_user.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["name"] == "Test Admin"
    
    def test_get_user_not_found(self, client, admin_token):
        """User nicht gefunden → 404"""
        response = client.get(
            f"/users/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestCreateUser:
    """Tests für POST /users/"""
    
    def test_create_user_success(self, client, admin_token, role_bedarfsmelder, department):
        """Admin kann User erstellen"""
        response = client.post(
            "/users/",
            json={
                "name": "Neuer Koch",
                "email": "neuer.koch@test.com",
                "password_plain": "sicherespasswort123",
                "role_id": str(role_bedarfsmelder.id),
                "department_id": str(department.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "neuer.koch@test.com"
        assert data["name"] == "Neuer Koch"
        assert "password_plain" not in data
        assert "password_hash" not in data
    
    def test_create_user_duplicate_email(self, client, admin_token, admin_user, role_admin, department):
        """Doppelte Email → Fehler"""
        response = client.post(
            "/users/",
            json={
                "name": "Doppelgänger",
                "email": "admin@test.com",  # Existiert schon!
                "password_plain": "test123",
                "role_id": str(role_admin.id),
                "department_id": str(department.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400
    
    def test_create_user_invalid_role(self, client, admin_token, department):
        """Ungültige Role → Fehler"""
        response = client.post(
            "/users/",
            json={
                "name": "Test",
                "email": "test@test.com",
                "password_plain": "test123",
                "role_id": str(uuid4()),  # Existiert nicht
                "department_id": str(department.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code in [400, 404]
    
    def test_create_user_not_admin(self, client, bedarfsmelder_token, role_bedarfsmelder, department):
        """Nicht-Admin kann keine User erstellen → 403"""
        response = client.post(
            "/users/",
            json={
                "name": "Versuch",
                "email": "versuch@test.com",
                "password_plain": "test123",
                "role_id": str(role_bedarfsmelder.id),
                "department_id": str(department.id)
            },
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403


class TestUpdateUser:
    """Tests für PATCH /users/{id}"""
    
    def test_update_user_success(self, client, admin_token, freigeber_user):
        """Admin kann User bearbeiten"""
        response = client.patch(
            f"/users/{freigeber_user.id}",
            json={"name": "Umbenannter Freigeber"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Umbenannter Freigeber"
    
    def test_update_user_email(self, client, admin_token, freigeber_user):
        """Email ändern"""
        response = client.patch(
            f"/users/{freigeber_user.id}",
            json={"email": "neue.email@test.com"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "neue.email@test.com"
    
    def test_update_user_not_found(self, client, admin_token):
        """User nicht gefunden → 404"""
        response = client.patch(
            f"/users/{uuid4()}",
            json={"name": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestDeleteUser:
    """Tests für DELETE /users/{id}"""
    
    def test_delete_user_success(self, client, admin_token, db, role_bedarfsmelder, department):
        """Admin kann User löschen (Soft Delete)"""
        # Neuen User zum Löschen erstellen
        user = User(
            id=uuid4(),
            name="Zum Löschen",
            email="loeschen@test.com",
            password_hash=hash_password("test123"),
            role_id=role_bedarfsmelder.id,
            department_id=department.id,
            is_active=True,
            is_2fa_enabled=False
        )
        db.add(user)
        db.commit()
        
        response = client.delete(
            f"/users/{user.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen ob deaktiviert (Soft Delete)
        db.refresh(user)
        assert user.is_active == False
    
    def test_delete_user_not_found(self, client, admin_token):
        """User nicht gefunden → 404"""
        response = client.delete(
            f"/users/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
    
    def test_delete_self_not_allowed(self, client, admin_token, admin_user):
        """Admin kann sich nicht selbst löschen"""
        response = client.delete(
            f"/users/{admin_user.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 400