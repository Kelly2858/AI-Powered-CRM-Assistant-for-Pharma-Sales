"""
Database models and setup for CRM HCP Module.
Uses SQLAlchemy with SQLite.
"""
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./crm_hcp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class HCP(Base):
    __tablename__ = "hcps"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    specialty = Column(String(200))
    affiliation = Column(String(300))
    location = Column(String(300))
    email = Column(String(200))
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, nullable=True)
    hcp_name = Column(String(200))
    rep_name = Column(String(200), default="Sales Rep")
    interaction_type = Column(String(100), default="Meeting")
    date = Column(String(50))
    time = Column(String(50), default="")
    attendees = Column(Text, default="[]")
    materials_shared = Column(Text, default="[]")
    samples_distributed = Column(Text, default="[]")
    topics_discussed = Column(Text, default="")
    outcomes = Column(Text, default="")
    follow_up_actions = Column(Text, default="[]")
    summary = Column(Text, default="")
    raw_transcript = Column(Text, default="")
    sentiment = Column(String(50), default="")
    sentiment_confidence = Column(Float, default=0.0)
    sentiment_reasoning = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, nullable=False)
    field_changed = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    edited_by = Column(String(200), default="Sales Rep")
    edited_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create tables and seed sample HCP data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(HCP).count() == 0:
        sample_hcps = [
            HCP(name="Dr. Rajesh Sharma", specialty="Cardiology", affiliation="AIIMS Delhi", location="New Delhi", email="r.sharma@aiims.in", phone="+91-9876543210"),
            HCP(name="Dr. Priya Patel", specialty="Oncology", affiliation="Tata Memorial Hospital", location="Mumbai", email="p.patel@tata.org", phone="+91-9876543211"),
            HCP(name="Dr. Anand Kumar", specialty="Neurology", affiliation="NIMHANS", location="Bangalore", email="a.kumar@nimhans.in", phone="+91-9876543212"),
            HCP(name="Dr. Sunita Reddy", specialty="Endocrinology", affiliation="Apollo Hospitals", location="Hyderabad", email="s.reddy@apollo.com", phone="+91-9876543213"),
            HCP(name="Dr. Vikram Singh", specialty="Orthopedics", affiliation="Fortis Hospital", location="Gurugram", email="v.singh@fortis.com", phone="+91-9876543214"),
            HCP(name="Dr. Meera Nair", specialty="Dermatology", affiliation="Amrita Hospital", location="Kochi", email="m.nair@amrita.in", phone="+91-9876543215"),
            HCP(name="Dr. Arjun Mehta", specialty="Pulmonology", affiliation="Medanta Hospital", location="Lucknow", email="a.mehta@medanta.org", phone="+91-9876543216"),
            HCP(name="Dr. Kavita Desai", specialty="Gastroenterology", affiliation="Kokilaben Hospital", location="Mumbai", email="k.desai@kokilaben.com", phone="+91-9876543217"),
            HCP(name="Dr. Sanjay Gupta", specialty="Cardiology", affiliation="Max Hospital", location="New Delhi", email="s.gupta@max.com", phone="+91-9876543218"),
            HCP(name="Dr. Lakshmi Iyer", specialty="Pediatrics", affiliation="Rainbow Children's Hospital", location="Chennai", email="l.iyer@rainbow.in", phone="+91-9876543219"),
        ]
        db.add_all(sample_hcps)
        db.commit()
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
