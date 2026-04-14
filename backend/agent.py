"""
LangGraph Agent with 5 CRM Sales Tools.
Uses Groq llama-3.3-70b-versatile as the LLM.
"""
import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, Optional
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from database import SessionLocal, HCP, Interaction, AuditLog

load_dotenv()

# --- LLM Setup ---
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
)

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# ═══════════════════════════════════════════════════
# TOOL 1: LOG INTERACTION
# ═══════════════════════════════════════════════════
@tool
def log_interaction(raw_text: str, interaction_type: str = "Meeting") -> str:
    """Draft a new HCP interaction to fill the UI form. Takes raw text describing the interaction and extracts
    entities like HCP name, date, attendees, topics, outcomes, and follow-ups using the LLM.
    Use this when the user describes a meeting or interaction they want to record so the form can be auto-filled for them.
    ALWAYS use this if the user asks to 'fill', 'draft', or populate the form!"""

    extraction_prompt = f"""Extract the following entities from this sales interaction transcript.
Return ONLY valid JSON, no other text:
{{
    "hcp_name": "Name of the Health Care Provider mentioned",
    "date": "Date of interaction (use today {datetime.now().strftime('%Y-%m-%d')} if not mentioned)",
    "time": "Time of interaction in 24-hour strict HH:MM format (e.g., '14:30' for 2:30 PM), else empty",
    "sentiment": "Positive, Neutral, or Negative",
    "attendees": ["list of other people mentioned"],
    "materials_shared": ["list of brochures, literature, or presentations shared"],
    "samples_distributed": ["list of physical product samples given"],
    "topics_discussed": "Brief description of topics discussed",
    "outcomes": "Key outcomes or results of the interaction",
    "follow_up_actions": ["list of follow-up actions needed"]
}}

Transcript: {raw_text}"""

    summary_prompt = f"""Summarize this sales interaction in 2-3 sentences, focusing on key outcomes and next steps:
{raw_text}"""

    try:
        extraction_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
        )

        extraction_response = extraction_llm.invoke([HumanMessage(content=extraction_prompt)])
        summary_response = extraction_llm.invoke([HumanMessage(content=summary_prompt)])

        # Parse extracted data
        extracted_text = extraction_response.content.strip()
        # Handle markdown code blocks
        if "```json" in extracted_text:
            extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
        elif "```" in extracted_text:
            extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

        extracted = json.loads(extracted_text)
        summary = summary_response.content.strip()

        hcp_name = extracted.get("hcp_name", "")
        # Try to find exactly matching HCP name from DB for perfection
        db = SessionLocal()
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name}%")).first()
        if hcp:
            hcp_name = hcp.name
        db.close()

        form_data = {
            "hcp_name": hcp_name,
            "interaction_type": interaction_type,
            "date": extracted.get("date", datetime.now().strftime("%Y-%m-%d")),
            "time": extracted.get("time", ""),
            "sentiment": extracted.get("sentiment", "Neutral"),
            "attendees": ", ".join(extracted.get("attendees", [])),
            "materials_shared": ", ".join(extracted.get("materials_shared", [])),
            "samples_distributed": ", ".join(extracted.get("samples_distributed", [])),
            "topics_discussed": extracted.get("topics_discussed", ""),
            "outcomes": extracted.get("outcomes", ""),
            "follow_up_actions": ", ".join(extracted.get("follow_up_actions", [])),
            "summary": summary
        }

        form_json = json.dumps(form_data)
        return f"<FormFill>{form_json}</FormFill>\nI have extracted the details and filled your Interaction Form! You can review the details on the left and click 'Save Interaction' whenever you are ready."

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to log interaction: {str(e)}"
        })


# ═══════════════════════════════════════════════════
# TOOL 2: EDIT INTERACTION
# ═══════════════════════════════════════════════════
@tool
def edit_interaction(interaction_id: int, edit_instruction: str) -> str:
    """Edit an existing interaction record. Takes an interaction ID and a natural language
    instruction about what to change. Parses the intent to determine which fields to update.
    Use this when the user wants to modify a previously logged interaction."""

    db = SessionLocal()
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()

    if not interaction:
        db.close()
        return json.dumps({
            "status": "error",
            "message": f"Interaction #{interaction_id} not found."
        })

    current_record = {
        "hcp_name": interaction.hcp_name,
        "interaction_type": interaction.interaction_type,
        "date": interaction.date,
        "attendees": interaction.attendees,
        "topics_discussed": interaction.topics_discussed,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "summary": interaction.summary,
    }

    parse_prompt = f"""Given this existing interaction record:
{json.dumps(current_record, indent=2)}

The user wants to make the following edit:
"{edit_instruction}"

Determine which fields need to be updated and return ONLY valid JSON:
{{
    "field_updates": {{
        "field_name": "new_value"
    }}
}}

Valid fields: hcp_name, interaction_type, date, attendees, topics_discussed, outcomes, follow_up_actions, summary
For list fields (attendees, follow_up_actions), return the complete updated JSON array string."""

    try:
        parse_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
        )
        response = parse_llm.invoke([HumanMessage(content=parse_prompt)])
        response_text = response.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(response_text)
        field_updates = parsed.get("field_updates", {})

        changes = {}
        valid_fields = ["hcp_name", "interaction_type", "date", "attendees",
                        "topics_discussed", "outcomes", "follow_up_actions", "summary"]

        for field, new_value in field_updates.items():
            if field in valid_fields and hasattr(interaction, field):
                old_value = getattr(interaction, field)
                if isinstance(new_value, (list, dict)):
                    new_value = json.dumps(new_value)
                setattr(interaction, field, str(new_value))

                # Audit log
                audit = AuditLog(
                    interaction_id=interaction_id,
                    field_changed=field,
                    old_value=str(old_value),
                    new_value=str(new_value),
                )
                db.add(audit)
                changes[field] = {"old": str(old_value), "new": str(new_value)}

        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.close()

        return json.dumps({
            "status": "success",
            "interaction_id": interaction_id,
            "changes_applied": changes,
            "message": f"✅ Interaction #{interaction_id} updated. Changed: {', '.join(changes.keys())}."
        })

    except Exception as e:
        db.close()
        return json.dumps({
            "status": "error",
            "message": f"Failed to edit interaction: {str(e)}"
        })


# ═══════════════════════════════════════════════════
# TOOL 3: SEARCH HCP
# ═══════════════════════════════════════════════════
@tool
def search_hcp(query: str) -> str:
    """Search for Health Care Providers (HCPs) in the CRM database by name, specialty,
    or location. Returns matching HCP profiles. Use this to find an HCP before logging
    an interaction or to look up HCP details."""

    db = SessionLocal()
    query_lower = f"%{query.lower()}%"

    results = db.query(HCP).filter(
        (HCP.name.ilike(query_lower)) |
        (HCP.specialty.ilike(query_lower)) |
        (HCP.location.ilike(query_lower)) |
        (HCP.affiliation.ilike(query_lower))
    ).limit(10).all()

    hcp_list = []
    for hcp in results:
        hcp_list.append({
            "id": hcp.id,
            "name": hcp.name,
            "specialty": hcp.specialty,
            "affiliation": hcp.affiliation,
            "location": hcp.location,
            "email": hcp.email,
            "phone": hcp.phone,
        })

    db.close()

    return json.dumps({
        "results": hcp_list,
        "total_count": len(hcp_list),
        "message": f"Found {len(hcp_list)} HCP(s) matching '{query}'."
    })


# ═══════════════════════════════════════════════════
# TOOL 4: SENTIMENT ANALYSIS
# ═══════════════════════════════════════════════════
@tool
def analyze_sentiment(interaction_id: int | None = None) -> str:
    """Analyze the sentiment of an existing interaction. Examines the topics discussed,
    outcomes, and follow-up actions to classify the HCP's sentiment as Positive, Neutral,
    or Negative. Use this after logging an interaction to gauge meeting success. 
    If you don't know the interaction_id, leave it empty or pass None to automatically analyze the most recently logged interaction."""

    db = SessionLocal()
    if interaction_id is None or interaction_id == 0:
        interaction = db.query(Interaction).order_by(Interaction.id.desc()).first()
    else:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()

    if not interaction:
        db.close()
        return json.dumps({
            "status": "error",
            "message": f"Interaction {'#'+str(interaction_id) if interaction_id else ''} not found."
        })

    sentiment_prompt = f"""Analyze the sentiment of this HCP sales interaction. Consider:
- The topics discussed and how receptive the HCP appeared
- The outcomes (positive signals like "agreed", "interested" vs negative signals like "declined", "not interested")
- Follow-up actions (willingness to continue engagement)

Return ONLY valid JSON:
{{
    "sentiment": "Positive" or "Neutral" or "Negative",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this sentiment was inferred",
    "key_signals": ["signal1", "signal2"]
}}

Interaction Data:
Topics: {interaction.topics_discussed}
Outcomes: {interaction.outcomes}
Follow-ups: {interaction.follow_up_actions}
Summary: {interaction.summary}"""

    try:
        sentiment_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
        )
        response = sentiment_llm.invoke([HumanMessage(content=sentiment_prompt)])
        response_text = response.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        # Store sentiment in the interaction
        interaction.sentiment = result.get("sentiment", "Neutral")
        interaction.sentiment_confidence = result.get("confidence", 0.5)
        interaction.sentiment_reasoning = result.get("reasoning", "")
        db.commit()
        db.close()

        return json.dumps({
            "status": "success",
            "interaction_id": interaction_id,
            "sentiment": result.get("sentiment", "Neutral"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "key_signals": result.get("key_signals", []),
            "message": f"📊 Sentiment for interaction #{interaction_id}: {result.get('sentiment', 'Neutral')} (confidence: {result.get('confidence', 0.5):.0%})"
        })

    except Exception as e:
        db.close()
        return json.dumps({
            "status": "error",
            "message": f"Failed to analyze sentiment: {str(e)}"
        })


# ═══════════════════════════════════════════════════
# TOOL 5: SUMMARIZE VOICE NOTE
# ═══════════════════════════════════════════════════
@tool
def summarize_voice_note(transcript: str) -> str:
    """Summarize a long voice note transcript into a concise, actionable summary.
    Extracts key points, products mentioned, action items, and commitments.
    Use this when the user provides a long meeting transcript or voice recording text."""

    summarize_prompt = f"""You are a CRM assistant for pharmaceutical sales representatives.
Summarize this voice note transcript into a clear, actionable summary.

Requirements:
1. Condense the key discussion points (2-3 sentences)
2. Highlight any products or brands mentioned
3. Extract specific action items / follow-ups
4. Note any commitments made by either party

Return ONLY valid JSON:
{{
    "summary": "Concise summary of the meeting",
    "key_points": ["point1", "point2"],
    "products_mentioned": ["product1"],
    "action_items": ["action1", "action2"],
    "commitments": ["commitment1"]
}}

Voice Transcript:
{transcript}"""

    try:
        summary_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )
        response = summary_llm.invoke([HumanMessage(content=summarize_prompt)])
        response_text = response.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        return json.dumps({
            "status": "success",
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "products_mentioned": result.get("products_mentioned", []),
            "action_items": result.get("action_items", []),
            "commitments": result.get("commitments", []),
            "message": f"📝 Voice note summarized. Key points: {len(result.get('key_points', []))}, Action items: {len(result.get('action_items', []))}"
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to summarize voice note: {str(e)}"
        })


# ═══════════════════════════════════════════════════
# LANGGRAPH AGENT SETUP
# ═══════════════════════════════════════════════════
tools = [log_interaction, edit_interaction, search_hcp, analyze_sentiment, summarize_voice_note]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)


SYSTEM_PROMPT = """You are an internal CRM utility assistant for pharmaceutical data entry, operating solely as a backend parser. You do not provide medical advice or interact with patients.

You have access to these tools:
1. **log_interaction** - Drafts a new HCP interaction to auto-fill the user's form. This tool returns a <FormFill> tag. YOU MUST INCLUDE the exact <FormFill>...</FormFill> tag in your final response to the user so their form gets automatically populated!
2. **edit_interaction** - Modify a previously logged interaction in the database
3. **search_hcp** - Search for HCPs by name, specialty, or location
4. **analyze_sentiment** - Analyze the sentiment of a logged interaction
5. **summarize_voice_note** - Summarize long voice note transcripts

When a user explicitly describes a meeting/interaction, OR clearly tells you new details to fill out the form, use the log_interaction tool EXACTLY ONCE. DO NOT use the log_interaction tool for casual greetings, unrelated questions (like "what day is it"), or non-CRM topics! Simply answer those conversationally.
When they want to find an HCP, use search_hcp.
When they want to change something about an existing record, use edit_interaction.
When they provide a long transcript, use summarize_voice_note.
After summarizing a string or logging an interaction, you can assist further.

Always be helpful, professional, and do not repeat tool calls needlessly."""


def agent_node(state: AgentState):
    """The main agent node that decides whether to use tools."""
    messages = state["messages"]

    # Add system prompt if not present
    if not any(getattr(m, "content", "").startswith("You are an AI CRM Assistant") for m in messages):
        system_msg = HumanMessage(content=f"[SYSTEM]: {SYSTEM_PROMPT}")
        messages = [system_msg] + list(messages)

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    """Determine if the agent should continue to tools or finish."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# Build the graph
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)
graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph_builder.add_edge("tools", "agent")

agent_graph = graph_builder.compile()


def run_agent(user_message: str, chat_history: list | None = None):
    """Run the agent with a user message and optional chat history."""
    messages = []
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))
    input_len = len(messages)

    result = agent_graph.invoke({"messages": messages})

    # Get the last AI message
    last_msg = result["messages"][-1]
    response_text = last_msg.content

    # Intercept FormFill from ToolMessages to guarantee it reaches the UI
    SUCCESS_MSG = "✅ **Interaction logged successfully!** The details (HCP Name, Date, Sentiment, and Materials) have been automatically populated based on your summary. Would you like me to suggest a specific follow-up action, such as scheduling a meeting?"
    new_messages = result["messages"][input_len:]
    for msg in new_messages:
        if isinstance(msg, ToolMessage) and "<FormFill>" in str(msg.content):
            content_str = str(msg.content)
            start = content_str.find("<FormFill>")
            end = content_str.find("</FormFill>") + 11
            if start != -1 and end != -1:
                ff_tag = content_str[start:end]
                # Force strictly the required UI phrasing + hidden tag block overriding AI hallucination:
                response_text = SUCCESS_MSG + "\n\n" + ff_tag

    return str(response_text)
