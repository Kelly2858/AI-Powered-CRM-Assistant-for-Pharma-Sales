# LangGraph Agent Tools — CRM HCP Module (Sales Activities)

## Overview

This document defines **five (5) specific tools** for the LangGraph-based AI agent powering the **Log Interaction Screen** of the CRM HCP Module. The agent uses the **Groq gemma2-9b-it** LLM and orchestrates these tools to help sales representatives capture, manage, and analyze interactions with Health Care Providers (HCPs).

---

## Architecture Diagram

```
┌─────────────────────────────────────┐
│         LangGraph Agent             │
│    (State Machine / Graph Flow)     │
│         LLM: Groq gemma2-9b-it     │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────┐  ┌──────────────┐  │
│  │ 1. Log       │  │ 2. Edit      │  │
│  │ Interaction  │  │ Interaction  │  │
│  └──────┬──────┘  └──────┬───────┘  │
│         │                │          │
│  ┌──────┴──────┐  ┌──────┴───────┐  │
│  │ 3. Search   │  │ 4. Sentiment │  │
│  │    HCP      │  │  Analysis    │  │
│  └──────┬──────┘  └──────┬───────┘  │
│         │                │          │
│         └──────┬─────────┘          │
│         ┌──────┴───────┐            │
│         │ 5. Summarize │            │
│         │  Voice Note  │            │
│         └──────────────┘            │
│                                     │
├──────────────┬──────────────────────┤
│              │                      │
│     ┌────────▼────────┐             │
│     │   PostgreSQL /  │             │
│     │     MySQL DB    │             │
│     └─────────────────┘             │
└─────────────────────────────────────┘
```

---

## Tool 1: Log Interaction (Required)

### Purpose
Captures and persists a complete interaction record between a sales representative and an HCP into the CRM database. This tool leverages the LLM extensively for **summarization**, **entity extraction**, and **structured data generation** from unstructured conversational input.

### Input Schema
```python
class LogInteractionInput(BaseModel):
    raw_text: str            # Free-form text, chat transcript, or voice note
    hcp_id: Optional[str]    # Pre-selected HCP ID (if already known)
    interaction_type: Optional[str]  # e.g., "In-Person", "Virtual", "Phone Call"
    date: Optional[str]      # Interaction date (auto-detected if not provided)
```

### How It Works (Step-by-Step)

1. **Raw Input Reception**: The tool accepts unstructured input—this could be a conversational chat message (e.g., *"I met Dr. Sharma at AIIMS today to discuss the new cardiac stent portfolio"*), a pasted voice transcript, or form field data.

2. **LLM-Powered Entity Extraction**: The Groq gemma2-9b-it model processes the raw text with a structured prompt to extract key entities:
   - **HCP Name** — Identified from the text (e.g., "Dr. Sharma")
   - **HCP Affiliation / Location** — (e.g., "AIIMS")
   - **Date of Interaction** — Parsed from the text or defaults to today
   - **Attendees** — Any other people mentioned in the interaction
   - **Products/Brands Discussed** — Specific products referenced (e.g., "cardiac stent portfolio")
   - **Topics Discussed** — Key discussion themes extracted and listed
   - **Outcomes** — Meeting results (e.g., "Dr. Sharma expressed interest in a trial")
   - **Follow-up Actions** — Next steps identified (e.g., "Send clinical data by Friday")

   **Example LLM Prompt**:
   ```
   Extract the following entities from this sales interaction transcript. 
   Return as JSON:
   {
     "hcp_name": "",
     "affiliation": "",
     "date": "",
     "attendees": [],
     "products_discussed": [],
     "topics_discussed": [],
     "outcomes": "",
     "follow_up_actions": []
   }
   Transcript: {raw_text}
   ```

3. **LLM-Powered Summarization**: The LLM generates a concise summary (2-3 sentences) of the entire interaction for quick reference:
   ```
   Summarize this sales interaction in 2-3 sentences, focusing on key outcomes 
   and next steps: {raw_text}
   ```

4. **HCP Resolution**: If `hcp_id` is not provided, the tool internally invokes the **Search HCP** tool using the extracted HCP name to resolve the correct HCP profile from the database.

5. **Database Persistence**: The structured data is saved to the `interactions` table:
   ```sql
   INSERT INTO interactions 
     (hcp_id, rep_id, interaction_type, date, attendees, 
      products_discussed, topics_discussed, outcomes, 
      follow_up_actions, summary, raw_transcript, created_at)
   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW());
   ```

6. **Confirmation Response**: The tool returns a structured confirmation with the logged data and interaction ID for reference.

### Output Schema
```python
class LogInteractionOutput(BaseModel):
    interaction_id: str
    status: str                    # "success" or "error"
    extracted_data: dict           # The structured entities extracted
    summary: str                   # LLM-generated summary
    hcp_matched: bool              # Whether HCP was auto-resolved
    message: str                   # Human-readable confirmation
```

---

## Tool 2: Edit Interaction (Required)

### Purpose
Allows modification of previously logged interaction data through conversational commands or direct field updates. The tool retrieves the existing record, determines which fields to update (using the LLM for intent parsing), applies changes, and persists the updated record.

### Input Schema
```python
class EditInteractionInput(BaseModel):
    interaction_id: str              # ID of the interaction to edit
    edit_instruction: Optional[str]  # Natural language edit command
    field_updates: Optional[dict]    # Direct field-value pairs to update
```

### How It Works (Step-by-Step)

1. **Record Retrieval**: The tool fetches the existing interaction record from the database using the `interaction_id`:
   ```sql
   SELECT * FROM interactions WHERE interaction_id = ?;
   ```

2. **Intent Parsing via LLM** (for conversational edits): When the user provides a natural language instruction like *"Change the outcome to 'Dr. Sharma agreed to a clinical trial' and add a follow-up to send the proposal by Monday"*, the LLM parses this into structured field updates:

   **Example LLM Prompt**:
   ```
   Given this existing interaction record:
   {existing_record_json}
   
   The user wants to make the following edit:
   "{edit_instruction}"
   
   Determine which fields need to be updated and return as JSON:
   {
     "field_updates": {
       "field_name": "new_value",
       ...
     }
   }
   
   Valid fields: outcomes, follow_up_actions, topics_discussed, 
   attendees, products_discussed, interaction_type, date, summary
   ```

3. **Validation**: The tool validates:
   - The interaction record exists
   - The requesting user has permission to edit it (rep ownership)
   - The field names are valid and values are in the correct format
   - Required fields are not being set to empty/null

4. **Delta Application**: Only the changed fields are updated in the database:
   ```sql
   UPDATE interactions 
   SET outcomes = ?, follow_up_actions = ?, updated_at = NOW()
   WHERE interaction_id = ?;
   ```

5. **Audit Trail**: The tool logs the edit action with before/after values for compliance:
   ```sql
   INSERT INTO interaction_audit_log 
     (interaction_id, field_changed, old_value, new_value, edited_by, edited_at)
   VALUES (?, ?, ?, ?, ?, NOW());
   ```

6. **Confirmation with Diff**: The tool returns the updated record along with a clear summary of what changed.

### Output Schema
```python
class EditInteractionOutput(BaseModel):
    interaction_id: str
    status: str                    # "success" or "error"
    changes_applied: dict          # {field: {old: ..., new: ...}}
    updated_record: dict           # Full updated record
    message: str                   # Human-readable confirmation
```

### Conversational Edit Examples
| User Says | Fields Updated |
|---|---|
| *"Change the outcome to agreed for trial"* | `outcomes` |
| *"Add Dr. Patel as an attendee"* | `attendees` (append) |
| *"Update the follow-up to schedule a call next Tuesday"* | `follow_up_actions` |
| *"The meeting date was actually March 15th, not 16th"* | `date` |

---

## Tool 3: Search HCP

### Purpose
Queries the CRM database to find and retrieve Health Care Provider profiles by name, specialty, location, or affiliation. This ensures interactions are linked to the correct HCP record and prevents duplicate entries.

### Input Schema
```python
class SearchHCPInput(BaseModel):
    query: str                     # Search term (name, specialty, location)
    search_type: Optional[str]     # "name", "specialty", "location", or "all"
    limit: Optional[int] = 10     # Max number of results
```

### How It Works

1. **Query Normalization**: The LLM normalizes the search query (handles abbreviations, typos, title variations like "Dr." / "Doctor"):
   ```
   Normalize this HCP search query for database lookup. 
   Handle abbreviations (Dr. → Doctor), common misspellings, 
   and return the cleaned search terms:
   Query: "{query}"
   ```

2. **Database Query**: Executes a fuzzy match search across the HCP table:
   ```sql
   SELECT hcp_id, name, specialty, affiliation, location, contact_info
   FROM hcps
   WHERE name ILIKE '%{query}%' 
      OR specialty ILIKE '%{query}%'
      OR location ILIKE '%{query}%'
      OR affiliation ILIKE '%{query}%'
   ORDER BY similarity(name, '{query}') DESC
   LIMIT ?;
   ```

3. **Result Ranking**: Results are ranked by relevance (name match > specialty match > location match).

4. **Return**: Returns a list of matching HCP profiles for the user/agent to select from.

### Output Schema
```python
class SearchHCPOutput(BaseModel):
    results: List[dict]    # List of matching HCP profiles
    total_count: int       # Total matches found
    message: str           # Human-readable result summary
```

---

## Tool 4: Sentiment Analysis

### Purpose
Analyzes the tone and sentiment of a logged interaction using the LLM. It evaluates the HCP's perceived sentiment (Positive, Neutral, Negative) based on the topics discussed, outcomes, and overall transcript, helping sales reps gauge the success of their meetings.

### Input Schema
```python
class SentimentAnalysisInput(BaseModel):
    interaction_id: Optional[str]  # Analyze an existing interaction
    text: Optional[str]            # Or analyze raw text directly
```

### How It Works

1. **Data Collection**: If `interaction_id` is provided, the tool retrieves the interaction's `topics_discussed`, `outcomes`, `follow_up_actions`, and `raw_transcript` from the database.

2. **LLM Sentiment Inference**: The Groq gemma2-9b-it model analyzes the combined text:

   **Example LLM Prompt**:
   ```
   Analyze the sentiment of this HCP sales interaction. Consider:
   - The topics discussed and how receptive the HCP appeared
   - The outcomes (positive signals like "agreed", "interested" vs 
     negative signals like "declined", "not interested")
   - Follow-up actions (willingness to continue engagement)
   
   Return as JSON:
   {
     "sentiment": "Positive" | "Neutral" | "Negative",
     "confidence": 0.0-1.0,
     "reasoning": "Brief explanation of why this sentiment was inferred",
     "key_signals": ["signal1", "signal2"]
   }
   
   Interaction Data:
   Topics: {topics_discussed}
   Outcomes: {outcomes}
   Follow-ups: {follow_up_actions}
   Transcript: {raw_transcript}
   ```

3. **Sentiment Storage**: The sentiment result is stored alongside the interaction record for reporting:
   ```sql
   UPDATE interactions 
   SET sentiment = ?, sentiment_confidence = ?, sentiment_reasoning = ?
   WHERE interaction_id = ?;
   ```

4. **Return**: Provides the sentiment classification along with reasoning and confidence.

### Output Schema
```python
class SentimentAnalysisOutput(BaseModel):
    sentiment: str             # "Positive", "Neutral", or "Negative"
    confidence: float          # 0.0 to 1.0
    reasoning: str             # Why this sentiment was inferred
    key_signals: List[str]     # E.g., ["agreed to trial", "asked for pricing"]
    message: str
```

---

## Tool 5: Summarize Voice Note

### Purpose
Condenses lengthy voice transcripts, meeting notes, or dictated observations into concise, actionable summaries. This allows sales reps to quickly capture the essence of a meeting without manually typing out detailed notes, and feeds directly into the **Log Interaction** workflow.

### Input Schema
```python
class SummarizeVoiceNoteInput(BaseModel):
    transcript: str               # Full voice note transcript text
    summary_length: Optional[str] # "brief" (1-2 sentences), "standard" (3-5), "detailed" (paragraph)
    extract_actions: bool = True  # Whether to also extract action items
```

### How It Works

1. **Transcript Preprocessing**: Cleans the raw transcript—removes filler words ("um", "uh", "like"), normalizes sentence breaks, and handles speech-to-text artifacts.

2. **LLM Summarization**: The Groq model generates a structured summary:

   **Example LLM Prompt**:
   ```
   You are a CRM assistant for pharmaceutical sales representatives.
   Summarize this voice note transcript into a clear, actionable summary.
   
   Requirements:
   1. Condense the key discussion points (2-3 sentences)
   2. Highlight any products or brands mentioned
   3. Extract specific action items / follow-ups
   4. Note any commitments made by either party
   
   Return as JSON:
   {
     "summary": "Concise summary of the meeting",
     "key_points": ["point1", "point2"],
     "products_mentioned": ["product1"],
     "action_items": ["action1", "action2"],
     "commitments": ["commitment1"]
   }
   
   Voice Transcript:
   {transcript}
   ```

3. **Action Item Extraction**: If enabled, the tool separately identifies and lists concrete follow-up tasks with deadlines (if mentioned).

4. **Return**: Provides the structured summary ready to be used by the **Log Interaction** tool or displayed directly to the user.

### Output Schema
```python
class SummarizeVoiceNoteOutput(BaseModel):
    summary: str                   # Concise summary
    key_points: List[str]          # Bullet-point key takeaways
    products_mentioned: List[str]  # Products/brands referenced
    action_items: List[str]        # Extracted follow-up tasks
    commitments: List[str]         # Mutual commitments identified
    message: str
```

---

## LangGraph Agent Flow — How Tools Interconnect

```
User Input (Chat / Form / Voice)
         │
         ▼
   ┌─────────────┐     Voice transcript?     ┌──────────────────┐
   │  Agent Node  │ ─────────────────────────▶│ Summarize Voice  │
   │  (Router)    │                           │      Note        │
   └──────┬──────┘                            └────────┬─────────┘
          │                                            │
          │ "Log this interaction"                     │ summarized text
          ▼                                            ▼
   ┌──────────────┐    need HCP lookup?     ┌──────────────┐
   │     Log      │ ──────────────────────▶ │  Search HCP  │
   │ Interaction  │ ◀────────────────────── │              │
   └──────┬───────┘    matched HCP ID       └──────────────┘
          │
          │ logged successfully
          ▼
   ┌──────────────┐
   │  Sentiment   │  ──▶ Stores sentiment with interaction
   │  Analysis    │
   └──────────────┘
          
          
   "Edit the outcome..."
          │
          ▼
   ┌──────────────┐
   │    Edit      │  ──▶ Updates specific fields + audit log
   │ Interaction  │
   └──────────────┘
```

---

## Summary Table

| # | Tool Name | Type | LLM Usage | Database Operations |
|---|-----------|------|-----------|-------------------|
| 1 | **Log Interaction** | Required | Entity Extraction, Summarization | INSERT interaction record |
| 2 | **Edit Interaction** | Required | Intent Parsing (NL → field updates) | SELECT + UPDATE record, INSERT audit log |
| 3 | **Search HCP** | Custom | Query Normalization | SELECT with fuzzy matching |
| 4 | **Sentiment Analysis** | Custom | Sentiment Classification | UPDATE sentiment fields |
| 5 | **Summarize Voice Note** | Custom | Text Summarization, Action Extraction | None (preprocessing tool) |
