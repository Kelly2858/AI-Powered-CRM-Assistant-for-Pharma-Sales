# AI-Powered CRM Assistant for Pharmaceutical Sales 💊🤖

This project is a fully-functional, modern CRM (Customer Relationship Management) system specifically designed for Pharmaceutical Sales Representatives. It integrates a smart, agentic AI Assistant that can read conversational text or medical voice-note transcripts and magically auto-fill your CRM logging forms without manual data entry.

## 🛠️ Technology Stack

### **Frontend**
- **React 18 + Vite:** Lightning-fast UI rendering and component hot-reloading.
- **Redux Toolkit:** Manages the active state of the application. It gracefully merges partial AI updates without overwriting existing, manually-typed form details.
- **Axios:** Handles asynchronous API interactions with the Python backend.
- **Vanilla CSS:** Beautiful, responsive glassmorphism aesthetic styling featuring dynamic UI cues (like glowing success chat bubbles for form fills).

### **Backend**
- **FastAPI:** High-performance REST Python framework serving the CRM database endpoints and chat streams.
- **SQLAlchemy:** The internal Object Relational Mapper for smoothly managing `Interactions` and `HCP` (Health Care Provider) profiles.
- **SQLite:** Embedded development database.

### **AI Layer (LangChain & Groq)**
- **LangGraph:** Powers the autonomous decision-making loops of the AI, allowing it to select specialized functions dynamically.
- **Groq (`llama-3.1-8b-instant`):** An incredibly fast, rate-limit friendly, state-of-the-art inferencing engine deployed for natural language processing, entity extraction, and sentiment tracking.

---

## 🔧 The 5 LangChain AI Tools

The AI Assistant has access to 5 specific back-end tools. When you speak to the assistant, the LangGraph node decides which tool is most appropriate to fulfill your request:

1. **`log_interaction`**
   - **Purpose:** Extracts entities (like HCP Name, Date, Attendees, Materials Shared, Outcomes, and Follow-ups) from a natural language transcript.
   - **Action:** Instead of just chatting back, the AI generates a strictly-formatted `JSON` response hidden inside a `<FormFill>` payload. The React frontend intercepts this payload and instantly binds the data to your UI Form inputs—ignoring empty fields so it doesn't accidentally erase your follow-up additions!

2. **`edit_interaction`**
   - **Purpose:** Modifies an existing log directly inside the SQLite database.
   - **Action:** If you tell the AI "Update the interaction with Dr. Naman to show he took 3 medicine samples," the AI will find that record's ID and safely push an overriding payload to the SQLAlchemy layer.

3. **`search_hcp`**
   - **Purpose:** Queries the embedded database for Health Care Providers.
   - **Action:** Quickly fetches profile context by matching Name, Specialty, or Location before you log a formal meeting.

4. **`analyze_sentiment`**
   - **Purpose:** Uses an LLM pass to classify a logged interaction's emotional trajectory.
   - **Action:** Can dynamically query the most recent interaction you just logged. It analyzes your *Topics*, *Outcomes*, and *Follow-ups* to objectively classify the interaction as **Positive**, **Neutral**, or **Negative**.

5. **`summarize_voice_note`**
   - **Purpose:** Cleans up massive blocks of raw text (e.g., if you dictate your entire 10-minute meeting to your phone).
   - **Action:** Extracts a bulleted summary, specifically targeting actionable commitments and products mentioned.

---

## ⚙️ How the Workflow Happens (End-to-End)

1. **User Input:** You type "I met Dr. Sharma today at 8:00 AM. We discussed the new cardiovascular drug. He gave positive sentiment and asked for a follow-up meeting on Friday."
2. **Backend Routing:** React sends this message string and your chat history to the `run_agent()` function inside `FastAPI`.
3. **Agent Logic (`LangGraph`):** The LLM reviews the 5 available tools and its rigid System Prompt. It realizes you are describing a meeting. It triggers the `log_interaction` tool.
4. **Data Extraction:** A secondary internal prompt strictly structures Dr. Sharma, 08:00 AM, and your outcomes into JSON.
5. **Success Override:** To prevent AI hallucination, Python intercepts the tool's success state, suppresses the normal chat output, and forcefully prepends a distinct success string: *"✅ Interaction logged successfully!..."* followed by the `<FormFill>` code block.
6. **Frontend Magic:** `ChatAssistant.jsx` receives the message. It detects `<FormFill>`, formats the chat bubble with a distinct green `success-msg` style, and dispatches the raw JSON to `updateFormData` in Redux. 
7. **Form Update:** The UI auto-populates magically. You verify the details in the visible side-panel form and click **Save Interaction** to officially push it to the Database.
