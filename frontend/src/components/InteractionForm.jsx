import { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions, updateFormData, clearFormData } from '../store/slices/interactionSlice';
import axios from 'axios';
import './InteractionForm.css';

const API_URL = 'http://localhost:8000/api';

export default function InteractionForm() {
  const dispatch = useDispatch();
  const formData = useSelector((state) => state.interactions.formData);
  const [hcpResults, setHcpResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const searchRef = useRef(null);

  const handleChange = (e) => {
    dispatch(updateFormData({ [e.target.name]: e.target.value }));
  };

  const searchHCP = async (query) => {
    if (query.length < 2) {
      setHcpResults([]);
      setShowDropdown(false);
      return;
    }
    try {
      const res = await axios.get(`${API_URL}/hcps?search=${encodeURIComponent(query)}`);
      setHcpResults(res.data);
      setShowDropdown(true);
    } catch (e) {
      setHcpResults([]);
    }
  };

  const selectHCP = (hcp) => {
    dispatch(updateFormData({ hcp_name: hcp.name }));
    setShowDropdown(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.hcp_name || !formData.topics_discussed) {
      setSavedMsg('⚠️ Please fill in HCP Name and Topics Discussed.');
      setTimeout(() => setSavedMsg(''), 3000);
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API_URL}/interactions`, formData);
      dispatch(fetchInteractions());
      setSavedMsg('✅ Interaction saved directly!');
      dispatch(clearFormData());
    } catch (error) {
      setSavedMsg('❌ Failed to save. Is the backend running?');
    }
    setSaving(false);
    setTimeout(() => setSavedMsg(''), 4000);
  };

  const handleClear = () => {
    dispatch(clearFormData());
    setSavedMsg('');
  };

  return (
    <div className="form-panel">
      <div className="form-panel-header">
        <span className="form-icon">📋</span>
        <h2>Interaction Details</h2>
      </div>

      {savedMsg && (
        <div className={`form-toast ${savedMsg.startsWith('✅') ? 'success' : savedMsg.startsWith('⚠') ? 'warning' : 'error'}`}>
          {savedMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="interaction-form">
        <div className="form-row">
          <div className="form-group">
            <label>HCP Name</label>
            <div className="search-input-wrapper" ref={searchRef}>
              <input
                type="text"
                name="hcp_name"
                value={formData.hcp_name}
                onChange={(e) => { handleChange(e); searchHCP(e.target.value); }}
                onFocus={() => formData.hcp_name.length >= 2 && setShowDropdown(true)}
                onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                placeholder="🔍 Search HCP..."
                autoComplete="off"
              />
              {showDropdown && hcpResults.length > 0 && (
                <div className="search-dropdown">
                  {hcpResults.map((hcp) => (
                    <div key={hcp.id} className="dropdown-item" onMouseDown={() => selectHCP(hcp)}>
                      <strong>{hcp.name}</strong>
                      <span>{hcp.specialty} • {hcp.affiliation}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="form-group">
            <label>Interaction Type</label>
            <select name="interaction_type" value={formData.interaction_type} onChange={handleChange}>
              <option value="Meeting">Meeting</option>
              <option value="Phone Call">Phone Call</option>
              <option value="Virtual">Virtual</option>
              <option value="Email">Email</option>
              <option value="Conference">Conference</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Date</label>
            <input type="date" name="date" value={formData.date} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label>Time</label>
            <input type="time" name="time" value={formData.time || ''} onChange={handleChange} onClick={(e) => e.target.showPicker && e.target.showPicker()} />
          </div>
        </div>

        <div className="form-group">
          <label>Attendees</label>
          <input type="text" name="attendees" value={formData.attendees} onChange={handleChange} placeholder="Enter names or search..." />
        </div>

        <div className="form-group">
          <label>Topics Discussed</label>
          <textarea name="topics_discussed" value={formData.topics_discussed} onChange={handleChange} rows={3} placeholder="Enter key discussion points..." />
          <div className="voice-note-link">🎙️ Summarize from Voice Note (Requires Consent)</div>
        </div>

        <div className="materials-section">
          <h4>Materials Shared / Samples Distributed</h4>
          <div className="form-group">
            <label>Materials Shared</label>
            <div className="input-with-button">
              <input type="text" name="materials_shared" value={formData.materials_shared || ''} onChange={handleChange} placeholder="Brochures." />
              <button type="button" className="btn-inline">🔍 Search/Add</button>
            </div>
          </div>
          <div className="form-group">
            <label>Samples Distributed</label>
            <div className="input-with-button">
              <input type="text" name="samples_distributed" value={formData.samples_distributed || ''} onChange={handleChange} placeholder="No samples added." />
              <button type="button" className="btn-inline">➕ Add Sample</button>
            </div>
          </div>
        </div>

        <div className="form-group">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className="sentiment-radio-group">
            <label>
              <input type="radio" name="sentiment" value="Positive" checked={formData.sentiment === 'Positive'} onChange={handleChange} />
              <span className="emoji">🟢</span> Positive
            </label>
            <label>
              <input type="radio" name="sentiment" value="Neutral" checked={formData.sentiment === 'Neutral'} onChange={handleChange} />
              <span className="emoji">⚪</span> Neutral
            </label>
            <label>
              <input type="radio" name="sentiment" value="Negative" checked={formData.sentiment === 'Negative'} onChange={handleChange} />
              <span className="emoji">🔴</span> Negative
            </label>
          </div>
        </div>

        <div className="form-group">
          <label>Outcomes</label>
          <textarea name="outcomes" value={formData.outcomes} onChange={handleChange} rows={3} placeholder="Key outcomes or agreements..." />
        </div>

        <div className="form-group">
          <label>Follow-up Actions</label>
          <textarea name="follow_up_actions" value={formData.follow_up_actions} onChange={handleChange} rows={2} placeholder="Next steps and actions..." />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={handleClear}>Clear</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? '⏳ Saving...' : '💾 Save Interaction'}
          </button>
        </div>
      </form>
    </div>
  );
}
