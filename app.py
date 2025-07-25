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
    comment = Column(String(100), nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class ScanRequest(BaseModel):
    host: str
    port: int = 443
    comment: Optional[str] = None
    
    @validator('host')
    def validate_host(cls, v):
        import re
        import ipaddress
        
        # Basic validation
        if not v or len(v) < 3:
            raise ValueError('Invalid host')
        
        # Remove any whitespace
        v = v.strip()
        
        # Check for dangerous characters that could be used in command injection
        # Even though we use subprocess list format, defense in depth is good
        dangerous_chars = ['$', '`', '\\', '"', "'", ';', '&', '|', '>', '<', '\n', '\r', '\t', '(', ')', '{', '}', '[', ']', '*', '?', '~', '!', '@', '#', '%', '^', '=', '+', ',', ':', ' ']
        if any(char in v for char in dangerous_chars):
            raise ValueError('Host contains invalid characters')
        
        # Check if it's an IP address
        try:
            ipaddress.ip_address(v)
            # Valid IP address (both IPv4 and IPv6)
            return v
        except ValueError:
            # Not an IP, check if it's a valid hostname/domain
            # Only allow: a-z, A-Z, 0-9, dots, and hyphens
            # Must start and end with alphanumeric
            hostname_regex = re.compile(
                r'^[a-zA-Z0-9]'  # Must start with alphanumeric
                r'[a-zA-Z0-9.-]*'  # Middle can have letters, numbers, dots, hyphens
                r'[a-zA-Z0-9]$'  # Must end with alphanumeric
            )
            if not hostname_regex.match(v) or '..' in v or '--' in v:
                raise ValueError('Invalid hostname format. Only letters, numbers, dots, and hyphens are allowed.')
        
        return v
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('comment')
    def validate_comment(cls, v):
        if v is None:
            return v
        
        # Strip whitespace
        v = v.strip()
        
        # Check length
        if len(v) > 100:
            raise ValueError('Comment must be 100 characters or less')
        
        # Sanitize - remove any control characters
        import string
        allowed_chars = string.printable
        v = ''.join(char for char in v if char in allowed_chars)
        
        return v

class ScanResponse(BaseModel):
    id: str
    host: str
    port: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    grade: Optional[str] = None
    error: Optional[str] = None
    comment: Optional[str] = None

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
            status="queued",
            comment=scan_request.comment
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
            created_at=db_scan.created_at,
            comment=scan_request.comment
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
            grade=scan.grade,
            comment=scan.comment
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
                grade=scan.grade,
                error=scan.error,
                comment=scan.comment
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
        
        if scan.status == "error":
            return {
                "id": scan.id,
                "host": scan.host,
                "port": scan.port,
                "status": scan.status,
                "error": scan.error,
                "completed_at": scan.completed_at
            }
        
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
            "completed_at": scan.completed_at,
            "comment": scan.comment
        }
    finally:
        db.close()

@app.get("/api/scans/{scan_id}/status")
async def get_scan_status(scan_id: str):
    # Check Redis for real-time status
    status = redis_client.get(f"scan:{scan_id}:status")
    progress = redis_client.get(f"scan:{scan_id}:progress")
    
    if status:
        # Also check database for error info if status is error
        if status == "error":
            db = SessionLocal()
            try:
                scan = db.query(Scan).filter(Scan.id == scan_id).first()
                if scan and scan.error:
                    return {
                        "id": scan_id,
                        "status": status,
                        "progress": int(progress) if progress else 0,
                        "error": scan.error,
                        "host": scan.host,
                        "port": scan.port
                    }
            finally:
                db.close()
        
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
        
        response = {
            "id": scan_id,
            "status": scan.status,
            "progress": 100 if scan.status in ["completed", "error"] else 0
        }
        
        # Include error info if present
        if scan.status == "error" and scan.error:
            response["error"] = scan.error
            response["host"] = scan.host
            response["port"] = scan.port
        
        return response
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)