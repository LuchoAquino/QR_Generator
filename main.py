from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import QRCode, Scan
from schemas import QRCodeCreate, QRCodeResponse, ScanResponse
import qrcode
import io
import base64
import string
import random
from datetime import datetime, timedelta
from typing import List

# Crear tablas al arrancar
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Tracker API", version="1.0.0")

# CORS para React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_short_code(length: int = 6) -> str:
    """Genera un código corto único para el QR."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "API de Generador de QR funcionando correctamente ✅"}


# ─── QR List  ─────────────────────────────────────────────────────────────────
# IMPORTANT: /api/qr/list MUST be declared BEFORE /api/qr/{short_code}
# to avoid FastAPI treating "list" as a path parameter.

@app.get("/api/qr/list")
def list_all_qrs(db: Session = Depends(get_db)):
    """Lista todos los QRs creados, ordenados por fecha descendente."""
    qrcodes = db.query(QRCode).order_by(QRCode.created_at.desc()).all()

    result = []
    for qr in qrcodes:
        scan_count = db.query(Scan).filter(Scan.qrcode_id == qr.id).count()
        result.append(
            {
                "id": qr.id,
                "url": qr.url,
                "short_code": qr.short_code,
                "created_at": qr.created_at,
                "scan_count": scan_count,
            }
        )

    return result


# ─── Create QR ────────────────────────────────────────────────────────────────

@app.post("/api/qr/create", response_model=QRCodeResponse, status_code=201)
def create_qr(data: QRCodeCreate, db: Session = Depends(get_db)):
    """Crea un nuevo QR para la URL indicada y devuelve sus datos."""
    # Garantizar que el short_code sea único
    while True:
        short_code = generate_short_code()
        if not db.query(QRCode).filter(QRCode.short_code == short_code).first():
            break

    db_qr = QRCode(url=data.url, short_code=short_code)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)

    return QRCodeResponse(
        id=db_qr.id,
        url=db_qr.url,
        short_code=db_qr.short_code,
        created_at=db_qr.created_at,
        scan_count=0,
    )


# ─── QR Image ─────────────────────────────────────────────────────────────────
# NOTE: /api/qr/{short_code}/image and /api/qr/{short_code}/stats MUST be
# declared BEFORE /api/qr/{short_code} so FastAPI doesn't swallow them.

@app.get("/api/qr/{short_code}/image")
def get_qr_image(short_code: str, request: Request, db: Session = Depends(get_db)):
    """Genera la imagen QR en base64 con la URL de tracking embebida."""
    qr = db.query(QRCode).filter(QRCode.short_code == short_code).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    # Construir la URL de tracking incluyendo el puerto si existe
    base = f"{request.url.scheme}://{request.url.hostname}"
    port = request.url.port
    if port and port not in (80, 443):
        base += f":{port}"
    tracking_url = f"{base}/track/{short_code}"

    # Generar imagen QR
    qr_img = qrcode.make(tracking_url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "image": f"data:image/png;base64,{img_base64}",
        "tracking_url": tracking_url,
    }


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/qr/{short_code}/stats")
def get_qr_stats(short_code: str, db: Session = Depends(get_db)):
    """Devuelve estadísticas de escaneos por día (últimos 30 días)."""
    qr = db.query(QRCode).filter(QRCode.short_code == short_code).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    total_scans = db.query(Scan).filter(Scan.qrcode_id == qr.id).count()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    scans_raw = (
        db.query(
            func.date(Scan.scanned_at).label("date"),
            func.count(Scan.id).label("count"),
        )
        .filter(Scan.qrcode_id == qr.id, Scan.scanned_at >= thirty_days_ago)
        .group_by(func.date(Scan.scanned_at))
        .order_by(func.date(Scan.scanned_at).desc())
        .all()
    )

    scans_by_date = [{"date": str(row.date), "count": row.count} for row in scans_raw]

    return {
        "id": qr.id,
        "short_code": qr.short_code,
        "url": qr.url,
        "total_scans": total_scans,
        "scans_by_date": scans_by_date,
    }


# ─── Delete QR ────────────────────────────────────────────────────────────────

@app.delete("/api/qr/{short_code}", status_code=204)
def delete_qr(short_code: str, db: Session = Depends(get_db)):
    """Elimina un QR y todos sus escaneos asociados."""
    qr = db.query(QRCode).filter(QRCode.short_code == short_code).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    db.delete(qr)
    db.commit()


# ─── Get single QR info ───────────────────────────────────────────────────────
# Keep this AFTER the sub-resource routes above.

@app.get("/api/qr/{short_code}", response_model=QRCodeResponse)
def get_qr(short_code: str, db: Session = Depends(get_db)):
    """Obtiene información básica de un QR por su código corto."""
    qr = db.query(QRCode).filter(QRCode.short_code == short_code).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    scan_count = db.query(Scan).filter(Scan.qrcode_id == qr.id).count()

    return QRCodeResponse(
        id=qr.id,
        url=qr.url,
        short_code=qr.short_code,
        created_at=qr.created_at,
        scan_count=scan_count,
    )


# ─── Track & Redirect ─────────────────────────────────────────────────────────

@app.get("/track/{short_code}")
def track_and_redirect(short_code: str, request: Request, db: Session = Depends(get_db)):
    """Registra el escaneo del QR y redirige a la URL original."""
    qr = db.query(QRCode).filter(QRCode.short_code == short_code).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    scan = Scan(qrcode_id=qr.id, scanned_at=datetime.utcnow())
    db.add(scan)
    db.commit()

    return RedirectResponse(url=qr.url, status_code=302)