from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db, init_db, Room

app = FastAPI(title="Grand Luxe Hotel API")


# --- Schemas ---
class RoomCreate(BaseModel):
    number: str
    type: str
    price_per_night: float


class RoomReserve(BaseModel):
    guest_name: str


class RoomResponse(BaseModel):
    id: int
    number: str
    type: str
    price_per_night: float
    status: str
    guest_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Startup ---
@app.on_event("startup")
def startup():
    init_db()


# --- API Routes ---
@app.get("/api/rooms", response_model=List[RoomResponse])
def get_rooms(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Room)
    if status:
        query = query.filter(Room.status == status)
    return query.order_by(Room.number).all()


@app.post("/api/rooms", response_model=RoomResponse, status_code=201)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    if room.type not in ("suite", "doble", "individual"):
        raise HTTPException(status_code=400, detail="Tipo inválido")
    if room.price_per_night <= 0:
        raise HTTPException(status_code=400, detail="El precio debe ser mayor a 0")
    existing = db.query(Room).filter(Room.number == room.number).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Ya existe una habitación con ese número"
        )
    new_room = Room(
        number=room.number, type=room.type, price_per_night=room.price_per_night
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@app.patch("/api/rooms/{room_id}/reserve", response_model=RoomResponse)
def reserve_room(room_id: int, data: RoomReserve, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    if room.status != "disponible":
        raise HTTPException(status_code=400, detail="La habitación no está disponible")
    room.status = "ocupada"
    room.guest_name = data.guest_name
    db.commit()
    db.refresh(room)
    return room


@app.patch("/api/rooms/{room_id}/release", response_model=RoomResponse)
def release_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    room.status = "disponible"
    room.guest_name = None
    db.commit()
    db.refresh(room)
    return room


@app.patch("/api/rooms/{room_id}/maintenance", response_model=RoomResponse)
def set_maintenance(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    room.status = "mantenimiento"
    room.guest_name = None
    db.commit()
    db.refresh(room)
    return room


@app.delete("/api/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    db.delete(room)
    db.commit()


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    rooms = db.query(Room).all()
    total = len(rooms)
    occupied = sum(1 for r in rooms if r.status == "ocupada")
    available = sum(1 for r in rooms if r.status == "disponible")
    maintenance = sum(1 for r in rooms if r.status == "mantenimiento")
    revenue = sum(r.price_per_night for r in rooms if r.status == "ocupada")
    return {
        "total": total,
        "occupied": occupied,
        "available": available,
        "maintenance": maintenance,
        "estimated_revenue": revenue,
    }


# --- Static frontend ---
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
