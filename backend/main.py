"""
FastAPI backend for CRM HCP Module.
Provides REST API endpoints and LangGraph agent chat interface.
"""
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from database import init_db, get_db, SessionLocal, HCP, Interaction, AuditLog
from agent import run_agent

app = FastAPI(title="CRM HCP Module", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    chat_history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    response: str
    status: str = "success"

class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str = "Meeting"
    date: str
    time: str = ""
    sentiment: str = "Neutral"
    attendees: str = ""
    materials_shared: str = ""
    samples_distributed: str = ""
    topics_discussed: str = ""
    outcomes: str = ""
    follow_up_actions: str = ""


class InteractionUpdate(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    summary: Optional[str] = None


# --- Startup ---
@app.on_event("startup")
def startup():
    init_db()
    print("✅ Database initialized with seed data.")


# --- Chat Endpoint (Main Agent Interface) ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the LangGraph CRM agent."""
    try:
        response = run_agent(request.message, request.chat_history)
        return ChatResponse(response=response, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Interaction Endpoints ---
@app.get("/api/interactions")
def list_interactions():
    """List all logged interactions."""
    db = SessionLocal()
    interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
    result = []
    for i in interactions:
        result.append({
            "id": i.id,
            "hcp_id": i.hcp_id,
            "hcp_name": i.hcp_name,
            "rep_name": i.rep_name,
            "interaction_type": i.interaction_type,
            "date": i.date,
            "time": i.time,
            "attendees": json.loads(i.attendees) if i.attendees else [],
            "materials_shared": json.loads(i.materials_shared) if i.materials_shared else [],
            "samples_distributed": json.loads(i.samples_distributed) if i.samples_distributed else [],
            "topics_discussed": i.topics_discussed,
            "outcomes": i.outcomes,
            "follow_up_actions": json.loads(i.follow_up_actions) if i.follow_up_actions else [],
            "summary": i.summary,
            "sentiment": i.sentiment,
            "sentiment_confidence": i.sentiment_confidence,
            "sentiment_reasoning": i.sentiment_reasoning,
            "created_at": str(i.created_at),
            "updated_at": str(i.updated_at),
        })
    db.close()
    return result

@app.post("/api/interactions")
def create_interaction(data: InteractionCreate):
    """Save an auto-filled interaction draft from the UI directly."""
    db = SessionLocal()
    hcp = db.query(HCP).filter(HCP.name.ilike(f"%{data.hcp_name}%")).first()
    hcp_id = hcp.id if hcp else None

    # Convert comma strings to JSON arrays
    attendees_list = [v.strip() for v in data.attendees.split(",") if v.strip()]
    materials_list = [v.strip() for v in data.materials_shared.split(",") if v.strip()]
    samples_list = [v.strip() for v in data.samples_distributed.split(",") if v.strip()]
    follow_up_list = [v.strip() for v in data.follow_up_actions.split(",") if v.strip()]

    new_interaction = Interaction(
        hcp_id=hcp_id,
        hcp_name=data.hcp_name,
        interaction_type=data.interaction_type,
        date=data.date,
        time=data.time,
        attendees=json.dumps(attendees_list),
        materials_shared=json.dumps(materials_list),
        samples_distributed=json.dumps(samples_list),
        topics_discussed=data.topics_discussed,
        outcomes=data.outcomes,
        follow_up_actions=json.dumps(follow_up_list),
        summary="",
        sentiment=data.sentiment,
        sentiment_confidence=1.0,
        raw_transcript="Manually saved from Form Draft."
    )
    db.add(new_interaction)
    db.commit()
    interaction_id = new_interaction.id
    db.close()
    return {"status": "success", "id": interaction_id}


@app.get("/api/interactions/{interaction_id}")
def get_interaction(interaction_id: int):
    """Get a single interaction by ID."""
    db = SessionLocal()
    i = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not i:
        db.close()
        raise HTTPException(status_code=404, detail="Interaction not found")
    result = {
        "id": i.id,
        "hcp_id": i.hcp_id,
        "hcp_name": i.hcp_name,
        "rep_name": i.rep_name,
        "interaction_type": i.interaction_type,
        "date": i.date,
        "attendees": json.loads(i.attendees) if i.attendees else [],
        "products_discussed": json.loads(i.products_discussed) if i.products_discussed else [],
        "topics_discussed": i.topics_discussed,
        "outcomes": i.outcomes,
        "follow_up_actions": json.loads(i.follow_up_actions) if i.follow_up_actions else [],
        "summary": i.summary,
        "sentiment": i.sentiment,
        "sentiment_confidence": i.sentiment_confidence,
        "sentiment_reasoning": i.sentiment_reasoning,
        "created_at": str(i.created_at),
        "updated_at": str(i.updated_at),
    }
    db.close()
    return result


@app.put("/api/interactions/{interaction_id}")
def update_interaction(interaction_id: int, update: InteractionUpdate):
    """Directly update an interaction (non-chat method)."""
    db = SessionLocal()
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        db.close()
        raise HTTPException(status_code=404, detail="Interaction not found")

    for field, value in update.dict(exclude_unset=True).items():
        if value is not None:
            old_value = getattr(interaction, field)
            setattr(interaction, field, value)
            audit = AuditLog(
                interaction_id=interaction_id,
                field_changed=field,
                old_value=str(old_value),
                new_value=str(value),
            )
            db.add(audit)

    db.commit()
    db.close()
    return {"status": "success", "message": f"Interaction #{interaction_id} updated."}


@app.delete("/api/interactions/{interaction_id}")
def delete_interaction(interaction_id: int):
    """Delete an interaction."""
    db = SessionLocal()
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        db.close()
        raise HTTPException(status_code=404, detail="Interaction not found")
    db.delete(interaction)
    db.commit()
    db.close()
    return {"status": "success", "message": f"Interaction #{interaction_id} deleted."}


# --- HCP Endpoints ---
@app.get("/api/hcps")
def list_hcps(search: Optional[str] = None):
    """List or search HCPs."""
    db = SessionLocal()
    query = db.query(HCP)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (HCP.name.ilike(search_filter)) |
            (HCP.specialty.ilike(search_filter)) |
            (HCP.location.ilike(search_filter)) |
            (HCP.affiliation.ilike(search_filter))
        )
    hcps = query.all()
    result = []
    for h in hcps:
        result.append({
            "id": h.id,
            "name": h.name,
            "specialty": h.specialty,
            "affiliation": h.affiliation,
            "location": h.location,
            "email": h.email,
            "phone": h.phone,
        })
    db.close()
    return result


@app.get("/api/hcps/{hcp_id}")
def get_hcp(hcp_id: int):
    """Get a single HCP by ID."""
    db = SessionLocal()
    h = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not h:
        db.close()
        raise HTTPException(status_code=404, detail="HCP not found")
    result = {
        "id": h.id,
        "name": h.name,
        "specialty": h.specialty,
        "affiliation": h.affiliation,
        "location": h.location,
        "email": h.email,
        "phone": h.phone,
    }
    db.close()
    return result


# --- Audit Log ---
@app.get("/api/audit-log/{interaction_id}")
def get_audit_log(interaction_id: int):
    """Get audit log entries for an interaction."""
    db = SessionLocal()
    logs = db.query(AuditLog).filter(AuditLog.interaction_id == interaction_id).order_by(AuditLog.edited_at.desc()).all()
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "interaction_id": log.interaction_id,
            "field_changed": log.field_changed,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "edited_by": log.edited_by,
            "edited_at": str(log.edited_at),
        })
    db.close()
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
