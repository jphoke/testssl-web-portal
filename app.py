from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, validator
from datetime import datetime
import os
import uuid
from typing import Optional, List
import redis
import json
from celery import Celery

# Initialize FastAPI app
app = FastAPI(title="SSL Test Portal", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ssluser:changeme@postgres:5432/ssltestportal")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
redis_client = redis.StrictRedis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

# Celery setup
celery_app = Celery('worker', broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))

# Database Models
class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(String, primary_key=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    grade = Column(String, nullable=True)
    results = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class ScanRequest(BaseModel):
    host: str
    port: int = 443
    
    @validator('host')
    def validate_host(cls, v):
        # Basic validation
        if not v or len(v) < 3:
            raise ValueError('Invalid host')
        return v
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

class ScanResponse(BaseModel):
    id: str
    host: str
    port: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    grade: Optional[str] = None

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "SSL Test Portal API", "version": "1.0.0"}

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": "connected",
            "redis": "connected"
        }
    }

@app.post("/api/scans", response_model=ScanResponse)
async def create_scan(scan_request: ScanRequest, background_tasks: BackgroundTasks):
    scan_id = str(uuid.uuid4())
    
    # Create database entry
    db = SessionLocal()
    try:
        db_scan = Scan(
            id=scan_id,
            host=scan_request.host,
            port=scan_request.port,
            status="queued"
        )
        db.add(db_scan)
        db.commit()
        
        # Queue the scan task
        celery_app.send_task('worker.run_ssl_scan', args=[scan_id, scan_request.host, scan_request.port])
        
        return ScanResponse(
            id=scan_id,
            host=scan_request.host,
            port=scan_request.port,
            status="queued",
            created_at=db_scan.created_at
        )
    finally:
        db.close()

@app.get("/api/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str):
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        return ScanResponse(
            id=scan.id,
            host=scan.host,
            port=scan.port,
            status=scan.status,
            created_at=scan.created_at,
            completed_at=scan.completed_at,
            grade=scan.grade
        )
    finally:
        db.close()

@app.get("/api/scans", response_model=List[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    try:
        scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
        return [
            ScanResponse(
                id=scan.id,
                host=scan.host,
                port=scan.port,
                status=scan.status,
                created_at=scan.created_at,
                completed_at=scan.completed_at,
                grade=scan.grade
            )
            for scan in scans
        ]
    finally:
        db.close()

@app.get("/api/scans/{scan_id}/results")
async def get_scan_results(scan_id: str):
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if scan.status != "completed":
            return {"status": scan.status, "message": "Scan not completed yet"}
        
        try:
            results = json.loads(scan.results) if scan.results else {}
        except:
            results = {"raw": scan.results}
        
        return {
            "id": scan.id,
            "host": scan.host,
            "port": scan.port,
            "status": scan.status,
            "grade": scan.grade,
            "results": results,
            "completed_at": scan.completed_at
        }
    finally:
        db.close()

@app.get("/api/scans/{scan_id}/status")
async def get_scan_status(scan_id: str):
    # Check Redis for real-time status
    status = redis_client.get(f"scan:{scan_id}:status")
    progress = redis_client.get(f"scan:{scan_id}:progress")
    
    if status:
        return {
            "id": scan_id,
            "status": status,
            "progress": int(progress) if progress else 0
        }
    
    # Fall back to database
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        return {
            "id": scan_id,
            "status": scan.status,
            "progress": 100 if scan.status == "completed" else 0
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)