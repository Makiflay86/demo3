from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./hotel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)  # suite, doble, individual
    price_per_night = Column(Float, nullable=False)
    status = Column(String, default="disponible")  # disponible, ocupada, mantenimiento
    created_at = Column(DateTime, default=datetime.utcnow)
    guest_name = Column(String, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Room).count() == 0:
        sample_rooms = [
            Room(
                number="101",
                type="individual",
                price_per_night=150.0,
                status="disponible",
            ),
            Room(
                number="201",
                type="doble",
                price_per_night=280.0,
                status="ocupada",
                guest_name="Carlos Méndez",
            ),
            Room(
                number="301", type="suite", price_per_night=580.0, status="disponible"
            ),
            Room(
                number="202",
                type="doble",
                price_per_night=260.0,
                status="mantenimiento",
            ),
            Room(
                number="401",
                type="suite",
                price_per_night=950.0,
                status="ocupada",
                guest_name="Elena Rojas",
            ),
        ]
        db.add_all(sample_rooms)
        db.commit()
    db.close()
