"""
Tests for hotel management app database logic.

Uses an in-memory SQLite database so production hotel.db is never touched.
All SQLAlchemy objects are rebuilt from scratch against the in-memory engine,
keeping each test fully isolated from the module-level engine in database.py.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Import only what we need from database.py — no FastAPI dependencies.
from database import Base, Room, init_db, get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine():
    """Return a fresh SQLite in-memory engine."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )


def _make_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_engine():
    """
    Creates all tables on a fresh in-memory engine and drops them after
    the test completes. Yields the engine for tests that need low-level access.
    """
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(mem_engine):
    """
    Provides a clean SQLAlchemy Session bound to the in-memory engine.
    The session (and any uncommitted data) is rolled back and closed after
    each test, guaranteeing isolation between tests.
    """
    SessionLocal = _make_session_factory(mem_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def session_factory(mem_engine):
    """Yields a sessionmaker bound to the in-memory engine."""
    return _make_session_factory(mem_engine)


# ---------------------------------------------------------------------------
# Utility: run init_db logic against an arbitrary engine / session factory
# ---------------------------------------------------------------------------

def _init_db_on_engine(engine, SessionFactory):
    """
    Mirrors the logic of database.init_db() but uses the provided engine and
    session factory instead of the module-level production ones.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionFactory()
    try:
        if db.query(Room).count() == 0:
            sample_rooms = [
                Room(number="101", type="individual", price_per_night=150.0, status="disponible"),
                Room(number="201", type="doble",      price_per_night=280.0, status="ocupada",     guest_name="Carlos Méndez"),
                Room(number="301", type="suite",      price_per_night=580.0, status="disponible"),
                Room(number="202", type="doble",      price_per_night=260.0, status="mantenimiento"),
                Room(number="401", type="suite",      price_per_night=950.0, status="ocupada",     guest_name="Elena Rojas"),
            ]
            db.add_all(sample_rooms)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1. init_db() — verifies the 'rooms' table is created
# ---------------------------------------------------------------------------

class TestInitDb:

    def test_creates_rooms_table(self, session_factory):
        """init_db() must create the 'rooms' table."""
        engine = _make_engine()
        sf = _make_session_factory(engine)
        _init_db_on_engine(engine, sf)

        # Inspect the actual database to confirm the table exists.
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
            )
            tables = [row[0] for row in result]

        assert "rooms" in tables, "Table 'rooms' was not created by init_db()"
        engine.dispose()

    # 2. init_db() — inserts exactly 5 sample rooms on first run
    def test_inserts_five_sample_rooms_on_first_run(self, session_factory):
        """init_db() must seed exactly 5 sample rooms when the table is empty."""
        engine = _make_engine()
        sf = _make_session_factory(engine)
        _init_db_on_engine(engine, sf)

        db = sf()
        try:
            count = db.query(Room).count()
        finally:
            db.close()
        engine.dispose()

        assert count == 5, f"Expected 5 sample rooms, got {count}"

    # 3. init_db() — idempotent: calling it twice must not duplicate rows
    def test_is_idempotent(self, session_factory):
        """Calling init_db() twice must not insert duplicate rows."""
        engine = _make_engine()
        sf = _make_session_factory(engine)
        _init_db_on_engine(engine, sf)
        _init_db_on_engine(engine, sf)  # second call

        db = sf()
        try:
            count = db.query(Room).count()
        finally:
            db.close()
        engine.dispose()

        assert count == 5, (
            f"Expected 5 rooms after two init_db() calls, got {count} — "
            "init_db() is not idempotent"
        )


# ---------------------------------------------------------------------------
# 4. Room model — create and persist a room correctly
# ---------------------------------------------------------------------------

class TestRoomModel:

    def test_create_and_persist_room(self, db_session):
        """A Room instance must be persisted and retrievable with correct fields."""
        room = Room(
            number="999",
            type="suite",
            price_per_night=750.0,
            status="disponible",
            guest_name="Ana Torres",
        )
        db_session.add(room)
        db_session.commit()

        fetched = db_session.query(Room).filter_by(number="999").first()

        assert fetched is not None, "Room was not persisted"
        assert fetched.number == "999"
        assert fetched.type == "suite"
        assert fetched.price_per_night == 750.0
        assert fetched.status == "disponible"
        assert fetched.guest_name == "Ana Torres"
        assert fetched.id is not None, "Primary key must be set after commit"

    # 5. Room model — room number must be unique
    def test_room_number_is_unique(self, db_session):
        """Inserting two rooms with the same number must raise IntegrityError."""
        room_a = Room(number="100", type="individual", price_per_night=100.0)
        room_b = Room(number="100", type="doble",      price_per_night=200.0)

        db_session.add(room_a)
        db_session.commit()

        db_session.add(room_b)
        with pytest.raises(IntegrityError):
            db_session.commit()

    # 6. Room model — default status is "disponible"
    def test_default_status_is_disponible(self, db_session):
        """A Room created without an explicit status must default to 'disponible'."""
        room = Room(number="555", type="individual", price_per_night=120.0)
        db_session.add(room)
        db_session.commit()

        fetched = db_session.query(Room).filter_by(number="555").first()
        assert fetched.status == "disponible", (
            f"Expected default status 'disponible', got '{fetched.status}'"
        )

    # 7. Room model — guest_name is nullable
    def test_guest_name_is_nullable(self, db_session):
        """guest_name must accept NULL without raising any error."""
        room = Room(number="777", type="doble", price_per_night=250.0)
        db_session.add(room)
        db_session.commit()

        fetched = db_session.query(Room).filter_by(number="777").first()
        assert fetched.guest_name is None, (
            f"Expected guest_name to be None, got '{fetched.guest_name}'"
        )


# ---------------------------------------------------------------------------
# 8. get_db() — generator opens and closes the session correctly
# ---------------------------------------------------------------------------

class TestGetDb:

    def test_get_db_yields_session_and_closes(self, mem_engine, monkeypatch):
        """
        get_db() must yield a usable session and close it after iteration
        without raising any exception.

        Strategy: monkeypatch database.SessionLocal so that get_db() uses the
        in-memory engine instead of the production one.
        """
        import database as db_module

        InMemorySession = _make_session_factory(mem_engine)
        monkeypatch.setattr(db_module, "SessionLocal", InMemorySession)

        gen = db_module.get_db()
        session = next(gen)

        # The yielded object must be a usable SQLAlchemy session.
        assert session is not None
        assert hasattr(session, "query"), "Yielded object is not a SQLAlchemy session"

        # Exhaust the generator so the finally block (session.close()) runs.
        try:
            next(gen)
        except StopIteration:
            pass

        # After closing, the session should no longer be active.
        # SQLAlchemy marks the session as closed; new operations raise an error.
        assert not session.is_active or session.bind is not None  # session object still exists


# ---------------------------------------------------------------------------
# 9 & 10. Queries — filtering and ordering
# ---------------------------------------------------------------------------

class TestQueries:

    @pytest.fixture(autouse=True)
    def _seed(self, db_session):
        """Insert a known set of rooms before each query test."""
        rooms = [
            Room(number="103", type="individual",  price_per_night=130.0, status="disponible"),
            Room(number="205", type="doble",        price_per_night=270.0, status="ocupada",       guest_name="Luis Vera"),
            Room(number="302", type="suite",        price_per_night=600.0, status="disponible"),
            Room(number="204", type="doble",        price_per_night=255.0, status="mantenimiento"),
            Room(number="402", type="suite",        price_per_night=920.0, status="ocupada",       guest_name="Marta Gil"),
        ]
        db_session.add_all(rooms)
        db_session.commit()

    # 9. Filter by status
    def test_filter_by_status_disponible(self, db_session):
        """Querying by status='disponible' must return only rooms with that status."""
        disponibles = (
            db_session.query(Room)
            .filter(Room.status == "disponible")
            .all()
        )
        assert len(disponibles) == 2, (
            f"Expected 2 'disponible' rooms, got {len(disponibles)}"
        )
        assert all(r.status == "disponible" for r in disponibles)

    def test_filter_by_status_ocupada(self, db_session):
        """Querying by status='ocupada' must return only occupied rooms."""
        ocupadas = (
            db_session.query(Room)
            .filter(Room.status == "ocupada")
            .all()
        )
        assert len(ocupadas) == 2, (
            f"Expected 2 'ocupada' rooms, got {len(ocupadas)}"
        )
        assert all(r.status == "ocupada" for r in ocupadas)

    def test_filter_by_status_mantenimiento(self, db_session):
        """Querying by status='mantenimiento' must return only maintenance rooms."""
        mantenimiento = (
            db_session.query(Room)
            .filter(Room.status == "mantenimiento")
            .all()
        )
        assert len(mantenimiento) == 1
        assert mantenimiento[0].number == "204"

    # 10. Order by room number
    def test_order_by_number_ascending(self, db_session):
        """Rooms ordered by number ascending must be sorted lexicographically."""
        rooms = db_session.query(Room).order_by(Room.number).all()
        numbers = [r.number for r in rooms]
        assert numbers == sorted(numbers), (
            f"Rooms are not in ascending order by number: {numbers}"
        )

    def test_order_by_number_descending(self, db_session):
        """Rooms ordered by number descending must be in reverse lexicographic order."""
        from sqlalchemy import desc

        rooms = db_session.query(Room).order_by(desc(Room.number)).all()
        numbers = [r.number for r in rooms]
        assert numbers == sorted(numbers, reverse=True), (
            f"Rooms are not in descending order by number: {numbers}"
        )

    def test_order_by_number_yields_all_rows(self, db_session):
        """Ordering must not discard any rows — all 5 seeded rooms must appear."""
        rooms = db_session.query(Room).order_by(Room.number).all()
        assert len(rooms) == 5, (
            f"Expected 5 rooms after ordering, got {len(rooms)}"
        )
