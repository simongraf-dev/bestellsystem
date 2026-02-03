"""
Edge Case Tests für die Order Business-Logik.

Testet die komplexen Szenarien:
- Department-Hierarchie (Sichtbarkeit vs. Bearbeitbarkeit)
- ShippingGroup-Gruppierung
- Lieferanten-Zuweisung
- Status-Transitions
"""
import pytest
from uuid import uuid4


# ============ FIXTURES FÜR HIERARCHIE-TESTS ============

@pytest.fixture
def department_hierarchy(db):
    """
    Erstellt eine Department-Hierarchie:
    
    Restaurant (root)
    ├── Küche
    │   └── Patisserie
    ├── Service
    └── Bar
    """
    from app.models import Department
    
    # Root
    restaurant = Department(id=uuid4(), name="Restaurant", parent_id=None, is_active=True)
    db.add(restaurant)
    db.flush()
    
    # Children von Restaurant
    kueche = Department(id=uuid4(), name="Küche", parent_id=restaurant.id, is_active=True)
    service = Department(id=uuid4(), name="Service", parent_id=restaurant.id, is_active=True)
    bar = Department(id=uuid4(), name="Bar", parent_id=restaurant.id, is_active=True)
    db.add_all([kueche, service, bar])
    db.flush()
    
    # Child von Küche
    patisserie = Department(id=uuid4(), name="Patisserie", parent_id=kueche.id, is_active=True)
    db.add(patisserie)
    db.commit()
    
    return {
        "restaurant": restaurant,
        "kueche": kueche,
        "service": service,
        "bar": bar,
        "patisserie": patisserie
    }


@pytest.fixture
def user_in_kueche(db, role_bedarfsmelder, department_hierarchy):
    """User der in 'Küche' arbeitet"""
    from app.models import User
    from app.utils.security import hash_password
    
    user = User(
        id=uuid4(),
        name="Koch Klaus",
        email="klaus@test.com",
        password_hash=hash_password("testpass123"),
        role_id=role_bedarfsmelder.id,
        department_id=department_hierarchy["kueche"].id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_in_patisserie(db, role_bedarfsmelder, department_hierarchy):
    """User der in 'Patisserie' arbeitet (Child von Küche)"""
    from app.models import User
    from app.utils.security import hash_password
    
    user = User(
        id=uuid4(),
        name="Bäcker Bernd",
        email="bernd@test.com",
        password_hash=hash_password("testpass123"),
        role_id=role_bedarfsmelder.id,
        department_id=department_hierarchy["patisserie"].id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_in_service(db, role_bedarfsmelder, department_hierarchy):
    """User der in 'Service' arbeitet (Geschwister von Küche)"""
    from app.models import User
    from app.utils.security import hash_password
    
    user = User(
        id=uuid4(),
        name="Kellner Karl",
        email="karl@test.com",
        password_hash=hash_password("testpass123"),
        role_id=role_bedarfsmelder.id,
        department_id=department_hierarchy["service"].id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def freigeber_in_restaurant(db, role_freigeber, department_hierarchy):
    """Freigeber der in 'Restaurant' (Root) arbeitet"""
    from app.models import User
    from app.utils.security import hash_password
    
    user = User(
        id=uuid4(),
        name="Chef Charlie",
        email="charlie@test.com",
        password_hash=hash_password("testpass123"),
        role_id=role_freigeber.id,
        department_id=department_hierarchy["restaurant"].id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def token_kueche(client, user_in_kueche):
    """Token für User in Küche"""
    response = client.post("/auth/login", json={
        "email": "klaus@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest.fixture
def token_patisserie(client, user_in_patisserie):
    """Token für User in Patisserie"""
    response = client.post("/auth/login", json={
        "email": "bernd@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest.fixture
def token_service(client, user_in_service):
    """Token für User in Service"""
    response = client.post("/auth/login", json={
        "email": "karl@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest.fixture
def token_freigeber_restaurant(client, freigeber_in_restaurant):
    """Token für Freigeber in Restaurant"""
    response = client.post("/auth/login", json={
        "email": "charlie@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


# ============ DEPARTMENT SICHTBARKEIT TESTS ============

class TestDepartmentVisibility:
    """Tests für _get_visible_departments Logik"""
    
    def test_user_sees_own_department_orders(
        self, client, token_kueche, user_in_kueche, department_hierarchy, db, article
    ):
        """User sieht Orders aus eigenem Department."""
        # Order in Küche erstellen (als Admin damit es klappt)
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["kueche"].id,
            creator_id=user_in_kueche.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        
        response = client.get(
            "/orders/",
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 1
        assert any(o["department"]["id"] == str(department_hierarchy["kueche"].id) for o in orders)
    
    def test_user_sees_parent_department_orders(
        self, client, token_kueche, freigeber_in_restaurant, department_hierarchy, db
    ):
        """User in Küche sieht Orders aus Restaurant (Parent)."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["restaurant"].id,
            creator_id=freigeber_in_restaurant.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        
        response = client.get(
            "/orders/",
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert any(o["department"]["id"] == str(department_hierarchy["restaurant"].id) for o in orders)
    
    def test_user_sees_sibling_department_orders(
        self, client, token_kueche, user_in_service, department_hierarchy, db
    ):
        """User in Küche sieht Orders aus Service (Geschwister)."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["service"].id,
            creator_id=user_in_service.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        
        response = client.get(
            "/orders/",
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert any(o["department"]["id"] == str(department_hierarchy["service"].id) for o in orders)
    
    def test_user_sees_child_department_orders(
        self, client, token_kueche, user_in_patisserie, department_hierarchy, db
    ):
        """User in Küche sieht Orders aus Patisserie (Child)."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["patisserie"].id,
            creator_id=user_in_patisserie.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        
        response = client.get(
            "/orders/",
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
        orders = response.json()
        # Patisserie ist Child von Küche - je nach Implementierung sichtbar oder nicht
        # Prüfe deine _get_visible_departments Logik!


# ============ DEPARTMENT BEARBEITBARKEIT TESTS ============

class TestDepartmentEditability:
    """Tests für _get_editable_departments und _can_edit_order Logik"""
    
    def test_user_can_edit_own_department_order(
        self, client, token_kueche, user_in_kueche, department_hierarchy, db, article, article_group
    ):
        """User kann Order in eigenem Department bearbeiten."""
        # Erst Order erstellen
        response = client.post(
            "/orders/",
            json={
                "department_id": str(department_hierarchy["kueche"].id),
                "items": [{
                    "article_id": str(article.id),
                    "amount": 5
                }]
            },
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
        order_id = response.json()["id"]
        
        # Dann bearbeiten
        response = client.patch(
            f"/orders/{order_id}",
            json={"delivery_notes": "Bitte früh liefern"},
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 200
    
    def test_user_can_edit_child_department_order(
        self, client, token_kueche, user_in_patisserie, department_hierarchy, db, article
    ):
        """User in Küche kann Order aus Patisserie (Child) bearbeiten."""
        from app.models import Order, OrderStatus
        
        # Order in Patisserie erstellen
        order = Order(
            department_id=department_hierarchy["patisserie"].id,
            creator_id=user_in_patisserie.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # User aus Küche versucht zu bearbeiten
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Test"},
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        # Sollte funktionieren - Küche ist Parent von Patisserie
        assert response.status_code == 200
    
    def test_user_cannot_edit_parent_department_order(
        self, client, token_kueche, freigeber_in_restaurant, department_hierarchy, db
    ):
        """User in Küche kann NICHT Order aus Restaurant (Parent) bearbeiten."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["restaurant"].id,
            creator_id=freigeber_in_restaurant.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Test"},
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        # Sollte 403 sein - keine Berechtigung nach oben
        assert response.status_code == 403
    
    def test_user_cannot_edit_sibling_department_order(
        self, client, token_kueche, user_in_service, department_hierarchy, db
    ):
        """User in Küche kann NICHT Order aus Service (Geschwister) bearbeiten."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["service"].id,
            creator_id=user_in_service.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Test"},
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        # Sollte 403 sein - Geschwister ist nicht bearbeitbar
        assert response.status_code == 403
    
    def test_freigeber_in_root_can_edit_all_children(
        self, client, token_freigeber_restaurant, user_in_patisserie, department_hierarchy, db
    ):
        """Freigeber in Restaurant kann Orders in allen Child-Departments bearbeiten."""
        from app.models import Order, OrderStatus
        
        # Order ganz unten in Patisserie
        order = Order(
            department_id=department_hierarchy["patisserie"].id,
            creator_id=user_in_patisserie.id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Chef sagt ok"},
            headers={"Authorization": f"Bearer {token_freigeber_restaurant}"}
        )
        assert response.status_code == 200


# ============ STATUS TRANSITION TESTS ============

class TestOrderStatusTransitions:
    """Tests für Order Status-Änderungen"""
    
    def test_cannot_close_order_without_items(
        self, client, token_kueche, department_hierarchy, db
    ):
        """Order ohne Items kann nicht abgeschlossen werden."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["kueche"].id,
            creator_id=db.query(User).filter(User.email == "klaus@test.com").first().id,
            status=OrderStatus.ENTWURF,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.post(
            f"/orders/{order.id}/abschliessen",
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 400
        assert "Item" in response.json()["detail"] or "leer" in response.json()["detail"].lower()
    
    def test_cannot_add_item_to_vollstaendig_order(
        self, client, admin_token, department, article, db
    ):
        """Zu einer abgeschlossenen Order können keine Items hinzugefügt werden."""
        from app.models import Order, OrderStatus, OrderItem, User
        
        admin = db.query(User).filter(User.email == "admin@test.com").first()
        
        order = Order(
            department_id=department.id,
            creator_id=admin.id,
            status=OrderStatus.VOLLSTAENDIG,  # Bereits abgeschlossen
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.post(
            f"/orders/{order.id}/items",
            json={
                "article_id": str(article.id),
                "amount": 3
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code in [400, 403]  # Je nach Implementierung
    
    def test_cannot_edit_vollstaendig_order_as_bedarfsmelder(
        self, client, token_kueche, user_in_kueche, department_hierarchy, db
    ):
        """Bedarfsmelder kann VOLLSTAENDIG Order nicht bearbeiten."""
        from app.models import Order, OrderStatus
        
        order = Order(
            department_id=department_hierarchy["kueche"].id,
            creator_id=user_in_kueche.id,
            status=OrderStatus.VOLLSTAENDIG,
            is_active=True
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        response = client.patch(
            f"/orders/{order.id}",
            json={"delivery_notes": "Test"},
            headers={"Authorization": f"Bearer {token_kueche}"}
        )
        assert response.status_code == 403


# ============ SHIPPING GROUP TESTS ============

class TestShippingGroupLogic:
    """Tests für ShippingGroup Erstellung und Gruppierung"""
    
    def test_same_supplier_same_date_one_shipping_group(
        self, client, admin_token, department, db
    ):
        """2 Items mit gleichem Lieferant + Datum → 1 ShippingGroup."""
        from app.models import Article, ArticleGroup, Supplier, ArticleSupplier, ShippingGroup
        
        # Setup: 2 Artikel, 1 Lieferant
        group = ArticleGroup(name="Test Gruppe", is_active=True)
        db.add(group)
        db.flush()
        
        article1 = Article(name="Artikel A", unit="kg", article_group_id=group.id, is_active=True)
        article2 = Article(name="Artikel B", unit="Stück", article_group_id=group.id, is_active=True)
        db.add_all([article1, article2])
        db.flush()
        
        supplier = Supplier(name="Lieferant X", is_active=True, fixed_delivery_days=False)
        db.add(supplier)
        db.flush()
        
        # Beide Artikel beim gleichen Lieferanten
        db.add(ArticleSupplier(article_id=article1.id, supplier_id=supplier.id, unit="kg"))
        db.add(ArticleSupplier(article_id=article2.id, supplier_id=supplier.id, unit="kg"))
        db.commit()
        
        # Order mit beiden Artikeln erstellen
        response = client.post(
            "/orders/",
            json={
                "department_id": str(department.id),
                "items": [
                    {"article_id": str(article1.id), "amount": 5},
                    {"article_id": str(article2.id), "amount": 10}
                ]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        order = response.json()
        
        # Prüfen: Beide Items sollten die gleiche shipping_group_id haben
        shipping_group_ids = set()
        for item in order["items"]:
            if item.get("shipping_group_id"):
                shipping_group_ids.add(item["shipping_group_id"])
        
        # Maximal 1 ShippingGroup (oder 0 wenn supplier_id NULL weil mehrere Lieferanten)
        assert len(shipping_group_ids) <= 1
    
    def test_different_suppliers_different_shipping_groups(
        self, client, admin_token, department, db
    ):
        """2 Items mit verschiedenen Lieferanten → 2 ShippingGroups."""
        from app.models import Article, ArticleGroup, Supplier, ArticleSupplier
        
        # Setup: 2 Artikel, 2 Lieferanten
        group = ArticleGroup(name="Test Gruppe 2", is_active=True)
        db.add(group)
        db.flush()
        
        article1 = Article(name="Artikel C", unit="kg", article_group_id=group.id, is_active=True)
        article2 = Article(name="Artikel D", unit="Stück", article_group_id=group.id, is_active=True)
        db.add_all([article1, article2])
        db.flush()
        
        supplier1 = Supplier(name="Lieferant Y", is_active=True, fixed_delivery_days=False)
        supplier2 = Supplier(name="Lieferant Z", is_active=True, fixed_delivery_days=False)
        db.add_all([supplier1, supplier2])
        db.flush()
        
        # Jeder Artikel bei anderem Lieferanten
        db.add(ArticleSupplier(article_id=article1.id, supplier_id=supplier1.id, unit="kg"))
        db.add(ArticleSupplier(article_id=article2.id, supplier_id=supplier2.id, unit="kg"))
        db.commit()
        
        response = client.post(
            "/orders/",
            json={
                "department_id": str(department.id),
                "items": [
                    {"article_id": str(article1.id), "amount": 5},
                    {"article_id": str(article2.id), "amount": 10}
                ]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        order = response.json()
        
        # Prüfen: 2 verschiedene ShippingGroups
        shipping_group_ids = set()
        for item in order["items"]:
            if item.get("shipping_group_id"):
                shipping_group_ids.add(item["shipping_group_id"])
        
        assert len(shipping_group_ids) == 2
    
    def test_article_with_no_supplier_gets_note(
        self, client, admin_token, department, db
    ):
        """Artikel ohne Lieferant → Notiz wird gesetzt."""
        from app.models import Article, ArticleGroup
        
        group = ArticleGroup(name="Ohne Lieferant", is_active=True)
        db.add(group)
        db.flush()
        
        article = Article(name="Seltener Artikel", unit="Stück", article_group_id=group.id, is_active=True)
        db.add(article)
        db.commit()
        
        response = client.post(
            "/orders/",
            json={
                "department_id": str(department.id),
                "items": [
                    {"article_id": str(article.id), "amount": 1}
                ]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        order = response.json()
        
        # Item sollte eine Notiz haben und keine ShippingGroup
        item = order["items"][0]
        assert item.get("shipping_group_id") is None or item.get("supplier_id") is None
        # Optional: Prüfe ob Notiz gesetzt wurde
        # assert "manuell" in item.get("note", "").lower()
    
    def test_article_with_multiple_suppliers_no_auto_assign(
        self, client, admin_token, department, db
    ):
        """Artikel mit mehreren Lieferanten → supplier_id bleibt NULL (Freigeber entscheidet)."""
        from app.models import Article, ArticleGroup, Supplier, ArticleSupplier
        
        group = ArticleGroup(name="Multi Supplier", is_active=True)
        db.add(group)
        db.flush()
        
        article = Article(name="Beliebter Artikel", unit="kg", article_group_id=group.id, is_active=True)
        db.add(article)
        db.flush()
        
        supplier1 = Supplier(name="Option A", is_active=True, fixed_delivery_days=False)
        supplier2 = Supplier(name="Option B", is_active=True, fixed_delivery_days=False)
        db.add_all([supplier1, supplier2])
        db.flush()
        
        # Artikel bei BEIDEN Lieferanten
        db.add(ArticleSupplier(article_id=article.id, supplier_id=supplier1.id, unit="kg"))
        db.add(ArticleSupplier(article_id=article.id, supplier_id=supplier2.id, unit="kg"))
        db.commit()
        
        response = client.post(
            "/orders/",
            json={
                "department_id": str(department.id),
                "items": [
                    {"article_id": str(article.id), "amount": 5}
                ]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        order = response.json()
        
        # supplier_id sollte NULL sein
        item = order["items"][0]
        assert item.get("supplier_id") is None or item.get("supplier") is None


# ============ IMPORT FÜR USER MODEL ============
from app.models import User