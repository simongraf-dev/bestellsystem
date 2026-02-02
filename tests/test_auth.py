"""
Tests für Auth Endpoints.

Testet:
- POST /auth/login
- POST /auth/refresh
- GET /auth/me
- 2FA Flow
"""
import pytest
from uuid import uuid4

from app.models import User
from app.utils.security import hash_password
from tests.conftest import auth_header


class TestLogin:
    """Tests für POST /auth/login"""
    
    def test_login_success(self, client, admin_user):
        """Erfolgreicher Login ohne 2FA"""
        response = client.post("/auth/login", json={
            "email": "admin@test.com",
            "password": "adminpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, admin_user):
        """Falsches Passwort → 401"""
        response = client.post("/auth/login", json={
            "email": "admin@test.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_login_user_not_found(self, client):
        """User existiert nicht → 401"""
        response = client.post("/auth/login", json={
            "email": "gibts@nicht.com",
            "password": "egal"
        })
        
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client, db, role_admin, department):
        """Inaktiver User → 401"""
        # Inaktiven User erstellen
        user = User(
            id=uuid4(),
            name="Inaktiv",
            email="inaktiv@test.com",
            password_hash=hash_password("test123"),
            role_id=role_admin.id,
            department_id=department.id,
            is_active=False,
            is_2fa_enabled=False
        )
        db.add(user)
        db.commit()
        
        response = client.post("/auth/login", json={
            "email": "inaktiv@test.com",
            "password": "test123"
        })
        
        assert response.status_code == 401
    
    def test_login_with_2fa_enabled(self, client, db, role_admin, department):
        """User mit 2FA → bekommt temp_token statt access_token"""
        import pyotp
        secret = pyotp.random_base32()
        
        user = User(
            id=uuid4(),
            name="2FA User",
            email="2fa@test.com",
            password_hash=hash_password("test123"),
            role_id=role_admin.id,
            department_id=department.id,
            is_active=True,
            is_2fa_enabled=True,
            totp_secret=secret
        )
        db.add(user)
        db.commit()
        
        response = client.post("/auth/login", json={
            "email": "2fa@test.com",
            "password": "test123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["requires_2fa"] == True
        assert "temp_token" in data
        assert data.get("access_token") is None


class TestRefreshToken:
    """Tests für POST /auth/refresh"""
    
    def test_refresh_success(self, client, admin_user):
        """Erfolgreicher Token Refresh"""
        # Erst login
        login_response = client.post("/auth/login", json={
            "email": "admin@test.com",
            "password": "adminpass123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Dann refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_refresh_invalid_token(self, client):
        """Ungültiger Refresh Token → 401"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        
        assert response.status_code == 401
    
    def test_refresh_with_access_token(self, client, admin_token):
        """Access Token statt Refresh Token → 401"""
        response = client.post("/auth/refresh", json={
            "refresh_token": admin_token  # Das ist ein access_token!
        })
        
        assert response.status_code == 401


class TestMe:
    """Tests für GET /auth/me"""
    
    def test_me_success(self, client, admin_token, admin_user):
        """Erfolgreicher Abruf der eigenen Daten"""
        response = client.get(
            "/auth/me",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["name"] == "Test Admin"
        assert data["role"]["name"] == "Admin"
        assert data["department"]["name"] == "Test-Küche"
    
    def test_me_without_auth(self, client):
        """Ohne Token → 401"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_me_invalid_token(self, client):
        """Ungültiger Token → 401"""
        response = client.get(
            "/auth/me",
            headers=auth_header("invalid.token.here")
        )
        
        assert response.status_code == 401


class Test2FAValidate:
    """Tests für POST /auth/2fa/validate"""
    
    def test_2fa_validate_success(self, client, db, role_admin, department):
        """Erfolgreiche 2FA Validierung"""
        import pyotp
        secret = pyotp.random_base32()
        
        user = User(
            id=uuid4(),
            name="2FA User",
            email="2fa@test.com",
            password_hash=hash_password("test123"),
            role_id=role_admin.id,
            department_id=department.id,
            is_active=True,
            is_2fa_enabled=True,
            totp_secret=secret
        )
        db.add(user)
        db.commit()
        
        # Login → temp_token bekommen
        login_response = client.post("/auth/login", json={
            "email": "2fa@test.com",
            "password": "test123"
        })
        temp_token = login_response.json()["temp_token"]
        
        # 2FA Code generieren
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        # Validieren
        response = client.post("/auth/2fa/validate", json={
            "temp_token": temp_token,
            "code": code
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_2fa_validate_wrong_code(self, client, db, role_admin, department):
        """Falscher 2FA Code → 401"""
        import pyotp
        secret = pyotp.random_base32()
        
        user = User(
            id=uuid4(),
            name="2FA User",
            email="2fa2@test.com",
            password_hash=hash_password("test123"),
            role_id=role_admin.id,
            department_id=department.id,
            is_active=True,
            is_2fa_enabled=True,
            totp_secret=secret
        )
        db.add(user)
        db.commit()
        
        # Login
        login_response = client.post("/auth/login", json={
            "email": "2fa2@test.com",
            "password": "test123"
        })
        temp_token = login_response.json()["temp_token"]
        
        # Falscher Code
        response = client.post("/auth/2fa/validate", json={
            "temp_token": temp_token,
            "code": "000000"
        })
        
        assert response.status_code == 401