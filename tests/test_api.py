"""
Tests for Grand Luxe Hotel API.

Strategy:
- Each test gets a completely fresh in-memory SQLite database via the
  `client` fixture, so tests are fully independent.
- The production `hotel.db` file is never touched.
- TestClient (synchronous) from fastapi.testclient is used throughout;
  no pytest-asyncio required.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# We need the app and the ORM pieces from the project root.
# sys.path manipulation is done here so the tests can be run from any
# working directory with:  pytest tests/
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import Base, get_db, Room  # noqa: E402
from main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    Provide a TestClient backed by a fresh in-memory SQLite database.

    The dependency override replaces every call to `get_db` with a session
    bound to the in-memory engine, and the override is removed after the
    test completes so the next test starts completely clean.
    """
    # New in-memory engine per test — data never persists between tests.
    #
    # StaticPool is required when using SQLite in-memory databases with
    # TestClient: the ASGI app runs in a worker thread, so without StaticPool
    # each Session would open its own connection and see an empty (tableless)
    # database.  StaticPool forces every session to reuse the same underlying
    # connection, giving every thread visibility into the same in-memory DB.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Create all tables (empty, no seed data).
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    # Cleanup: remove override and drop tables so the engine can be GC'd.
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client_with_rooms(client):
    """
    Same TestClient but pre-populated with three rooms covering all statuses:
      - "101" individual  disponible
      - "201" doble       ocupada     (guest: "Ana García")
      - "301" suite       mantenimiento
    Returns a tuple (client, room_ids) where room_ids is a dict keyed by
    room number.
    """
    rooms_payload = [
        {"number": "101", "type": "individual", "price_per_night": 150.0},
        {"number": "201", "type": "doble",       "price_per_night": 280.0},
        {"number": "301", "type": "suite",        "price_per_night": 580.0},
    ]
    ids = {}
    for payload in rooms_payload:
        r = client.post("/api/rooms", json=payload)
        assert r.status_code == 201
        data = r.json()
        ids[data["number"]] = data["id"]

    # Reserve room 201.
    client.patch(f"/api/rooms/{ids['201']}/reserve", json={"guest_name": "Ana García"})
    # Put room 301 in maintenance.
    client.patch(f"/api/rooms/{ids['301']}/maintenance")

    return client, ids


# ===========================================================================
# GET /api/rooms
# ===========================================================================

class TestGetRooms:
    def test_get_rooms_empty(self, client):
        """Returns an empty list when no rooms exist."""
        r = client.get("/api/rooms")
        assert r.status_code == 200
        assert r.json() == []

    def test_get_rooms_returns_all(self, client_with_rooms):
        c, ids = client_with_rooms
        r = c.get("/api/rooms")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_get_rooms_ordered_by_number(self, client_with_rooms):
        """Rooms are returned ordered alphabetically by room number."""
        c, _ = client_with_rooms
        numbers = [room["number"] for room in c.get("/api/rooms").json()]
        assert numbers == sorted(numbers)

    def test_get_rooms_response_schema(self, client_with_rooms):
        """Every room object contains the expected fields."""
        c, _ = client_with_rooms
        room = c.get("/api/rooms").json()[0]
        assert set(room.keys()) == {"id", "number", "type", "price_per_night", "status", "guest_name"}

    def test_get_rooms_filter_disponible(self, client_with_rooms):
        c, _ = client_with_rooms
        r = c.get("/api/rooms?status=disponible")
        assert r.status_code == 200
        rooms = r.json()
        assert len(rooms) == 1
        assert all(room["status"] == "disponible" for room in rooms)

    def test_get_rooms_filter_ocupada(self, client_with_rooms):
        c, _ = client_with_rooms
        r = c.get("/api/rooms?status=ocupada")
        assert r.status_code == 200
        rooms = r.json()
        assert len(rooms) == 1
        assert rooms[0]["status"] == "ocupada"
        assert rooms[0]["guest_name"] == "Ana García"

    def test_get_rooms_filter_mantenimiento(self, client_with_rooms):
        c, _ = client_with_rooms
        r = c.get("/api/rooms?status=mantenimiento")
        assert r.status_code == 200
        rooms = r.json()
        assert len(rooms) == 1
        assert rooms[0]["status"] == "mantenimiento"

    def test_get_rooms_filter_unknown_status_returns_empty(self, client_with_rooms):
        """A status value that no room has should return an empty list, not an error."""
        c, _ = client_with_rooms
        r = c.get("/api/rooms?status=inexistente")
        assert r.status_code == 200
        assert r.json() == []


# ===========================================================================
# POST /api/rooms
# ===========================================================================

class TestCreateRoom:
    def test_create_room_success(self, client):
        payload = {"number": "101", "type": "individual", "price_per_night": 150.0}
        r = client.post("/api/rooms", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["number"] == "101"
        assert data["type"] == "individual"
        assert data["price_per_night"] == 150.0
        assert data["status"] == "disponible"
        assert data["guest_name"] is None
        assert isinstance(data["id"], int)

    def test_create_room_suite(self, client):
        r = client.post("/api/rooms", json={"number": "401", "type": "suite", "price_per_night": 950.0})
        assert r.status_code == 201
        assert r.json()["type"] == "suite"

    def test_create_room_doble(self, client):
        r = client.post("/api/rooms", json={"number": "202", "type": "doble", "price_per_night": 260.0})
        assert r.status_code == 201
        assert r.json()["type"] == "doble"

    def test_create_room_duplicate_number(self, client):
        payload = {"number": "101", "type": "individual", "price_per_night": 150.0}
        client.post("/api/rooms", json=payload)
        r = client.post("/api/rooms", json=payload)
        assert r.status_code == 400
        assert "número" in r.json()["detail"]

    def test_create_room_invalid_type(self, client):
        r = client.post("/api/rooms", json={"number": "999", "type": "penthouse", "price_per_night": 500.0})
        assert r.status_code == 400
        assert r.json()["detail"] == "Tipo inválido"

    def test_create_room_invalid_price_zero(self, client):
        r = client.post("/api/rooms", json={"number": "999", "type": "individual", "price_per_night": 0})
        assert r.status_code == 400
        assert "precio" in r.json()["detail"]

    def test_create_room_invalid_price_negative(self, client):
        r = client.post("/api/rooms", json={"number": "999", "type": "individual", "price_per_night": -100.0})
        assert r.status_code == 400
        assert "precio" in r.json()["detail"]

    def test_create_room_missing_fields(self, client):
        """Sending an incomplete body should return 422 Unprocessable Entity."""
        r = client.post("/api/rooms", json={"number": "101"})
        assert r.status_code == 422


# ===========================================================================
# PATCH /api/rooms/{id}/reserve
# ===========================================================================

class TestReserveRoom:
    def test_reserve_room_success(self, client_with_rooms):
        c, ids = client_with_rooms
        room_id = ids["101"]  # status: disponible
        r = c.patch(f"/api/rooms/{room_id}/reserve", json={"guest_name": "Luis Pérez"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ocupada"
        assert data["guest_name"] == "Luis Pérez"
        assert data["id"] == room_id

    def test_reserve_room_persisted(self, client_with_rooms):
        """After reserving, GET /api/rooms reflects the new state."""
        c, ids = client_with_rooms
        c.patch(f"/api/rooms/{ids['101']}/reserve", json={"guest_name": "Luis Pérez"})
        rooms = c.get("/api/rooms?status=ocupada").json()
        numbers = [r["number"] for r in rooms]
        assert "101" in numbers

    def test_reserve_room_not_available(self, client_with_rooms):
        """Trying to reserve an already-occupied room returns 400."""
        c, ids = client_with_rooms
        room_id = ids["201"]  # status: ocupada
        r = c.patch(f"/api/rooms/{room_id}/reserve", json={"guest_name": "Otro Huésped"})
        assert r.status_code == 400
        assert "disponible" in r.json()["detail"]

    def test_reserve_room_maintenance_not_available(self, client_with_rooms):
        """A room in maintenance is also not 'disponible' and cannot be reserved."""
        c, ids = client_with_rooms
        room_id = ids["301"]  # status: mantenimiento
        r = c.patch(f"/api/rooms/{room_id}/reserve", json={"guest_name": "Test Guest"})
        assert r.status_code == 400
        assert "disponible" in r.json()["detail"]

    def test_reserve_room_not_found(self, client):
        r = client.patch("/api/rooms/9999/reserve", json={"guest_name": "Nadie"})
        assert r.status_code == 404
        assert r.json()["detail"] == "Habitación no encontrada"

    def test_reserve_room_missing_guest_name(self, client_with_rooms):
        """Omitting guest_name should return 422."""
        c, ids = client_with_rooms
        r = c.patch(f"/api/rooms/{ids['101']}/reserve", json={})
        assert r.status_code == 422


# ===========================================================================
# PATCH /api/rooms/{id}/release
# ===========================================================================

class TestReleaseRoom:
    def test_release_room_success(self, client_with_rooms):
        c, ids = client_with_rooms
        room_id = ids["201"]  # status: ocupada
        r = c.patch(f"/api/rooms/{room_id}/release")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "disponible"
        assert data["guest_name"] is None

    def test_release_room_persisted(self, client_with_rooms):
        c, ids = client_with_rooms
        c.patch(f"/api/rooms/{ids['201']}/release")
        rooms = c.get("/api/rooms?status=disponible").json()
        numbers = [r["number"] for r in rooms]
        assert "201" in numbers

    def test_release_room_from_maintenance(self, client_with_rooms):
        """Releasing a maintenance room should also set it to disponible."""
        c, ids = client_with_rooms
        room_id = ids["301"]  # status: mantenimiento
        r = c.patch(f"/api/rooms/{room_id}/release")
        assert r.status_code == 200
        assert r.json()["status"] == "disponible"

    def test_release_room_not_found(self, client):
        r = client.patch("/api/rooms/9999/release")
        assert r.status_code == 404
        assert r.json()["detail"] == "Habitación no encontrada"


# ===========================================================================
# PATCH /api/rooms/{id}/maintenance
# ===========================================================================

class TestMaintenanceRoom:
    def test_maintenance_room_success_from_disponible(self, client_with_rooms):
        c, ids = client_with_rooms
        room_id = ids["101"]  # status: disponible
        r = c.patch(f"/api/rooms/{room_id}/maintenance")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "mantenimiento"
        assert data["guest_name"] is None

    def test_maintenance_room_success_from_ocupada(self, client_with_rooms):
        """An occupied room can be moved to maintenance; guest_name is cleared."""
        c, ids = client_with_rooms
        room_id = ids["201"]  # status: ocupada, guest_name set
        r = c.patch(f"/api/rooms/{room_id}/maintenance")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "mantenimiento"
        assert data["guest_name"] is None

    def test_maintenance_room_persisted(self, client_with_rooms):
        c, ids = client_with_rooms
        c.patch(f"/api/rooms/{ids['101']}/maintenance")
        rooms = c.get("/api/rooms?status=mantenimiento").json()
        numbers = [r["number"] for r in rooms]
        assert "101" in numbers

    def test_maintenance_room_not_found(self, client):
        r = client.patch("/api/rooms/9999/maintenance")
        assert r.status_code == 404
        assert r.json()["detail"] == "Habitación no encontrada"


# ===========================================================================
# DELETE /api/rooms/{id}
# ===========================================================================

class TestDeleteRoom:
    def test_delete_room_success(self, client_with_rooms):
        c, ids = client_with_rooms
        room_id = ids["101"]
        r = c.delete(f"/api/rooms/{room_id}")
        assert r.status_code == 204
        # Body must be empty for 204.
        assert r.content == b""

    def test_delete_room_actually_removed(self, client_with_rooms):
        c, ids = client_with_rooms
        room_id = ids["101"]
        c.delete(f"/api/rooms/{room_id}")
        r = c.get("/api/rooms")
        remaining_ids = [room["id"] for room in r.json()]
        assert room_id not in remaining_ids

    def test_delete_room_count_decreases(self, client_with_rooms):
        c, ids = client_with_rooms
        before = len(c.get("/api/rooms").json())
        c.delete(f"/api/rooms/{ids['101']}")
        after = len(c.get("/api/rooms").json())
        assert after == before - 1

    def test_delete_room_not_found(self, client):
        r = client.delete("/api/rooms/9999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Habitación no encontrada"

    def test_delete_room_idempotent_second_call_404(self, client_with_rooms):
        """Deleting the same room twice: second call must return 404."""
        c, ids = client_with_rooms
        room_id = ids["101"]
        c.delete(f"/api/rooms/{room_id}")
        r = c.delete(f"/api/rooms/{room_id}")
        assert r.status_code == 404


# ===========================================================================
# GET /api/stats
# ===========================================================================

class TestStats:
    def test_stats_empty_db(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.json()
        assert data == {
            "total": 0,
            "occupied": 0,
            "available": 0,
            "maintenance": 0,
            "estimated_revenue": 0.0,
        }

    def test_stats_all_fields_present(self, client_with_rooms):
        c, _ = client_with_rooms
        data = c.get("/api/stats").json()
        assert set(data.keys()) == {"total", "occupied", "available", "maintenance", "estimated_revenue"}

    def test_stats_total(self, client_with_rooms):
        c, _ = client_with_rooms
        assert c.get("/api/stats").json()["total"] == 3

    def test_stats_occupied(self, client_with_rooms):
        """Room 201 was reserved in the fixture."""
        c, _ = client_with_rooms
        assert c.get("/api/stats").json()["occupied"] == 1

    def test_stats_available(self, client_with_rooms):
        """Only room 101 is disponible."""
        c, _ = client_with_rooms
        assert c.get("/api/stats").json()["available"] == 1

    def test_stats_maintenance(self, client_with_rooms):
        """Room 301 was put in maintenance in the fixture."""
        c, _ = client_with_rooms
        assert c.get("/api/stats").json()["maintenance"] == 1

    def test_stats_estimated_revenue(self, client_with_rooms):
        """
        Only occupied rooms contribute to revenue.
        Room 201 (doble) costs 280.0 per night.
        """
        c, _ = client_with_rooms
        assert c.get("/api/stats").json()["estimated_revenue"] == pytest.approx(280.0)

    def test_stats_revenue_updates_after_reserve(self, client_with_rooms):
        """Reserving room 101 (150.0) adds to estimated_revenue."""
        c, ids = client_with_rooms
        c.patch(f"/api/rooms/{ids['101']}/reserve", json={"guest_name": "Nuevo Huésped"})
        revenue = c.get("/api/stats").json()["estimated_revenue"]
        assert revenue == pytest.approx(280.0 + 150.0)

    def test_stats_revenue_updates_after_release(self, client_with_rooms):
        """Releasing room 201 removes its price from estimated_revenue."""
        c, ids = client_with_rooms
        c.patch(f"/api/rooms/{ids['201']}/release")
        revenue = c.get("/api/stats").json()["estimated_revenue"]
        assert revenue == pytest.approx(0.0)

    def test_stats_after_delete(self, client_with_rooms):
        """Deleting a room decreases total and its category counter."""
        c, ids = client_with_rooms
        c.delete(f"/api/rooms/{ids['101']}")
        data = c.get("/api/stats").json()
        assert data["total"] == 2
        assert data["available"] == 0
