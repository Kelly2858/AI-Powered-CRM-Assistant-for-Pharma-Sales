import { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchInteractions, deleteInteraction } from '../store/slices/interactionSlice';
import './InteractionList.css';

export default function InteractionList() {
  const dispatch = useDispatch();
  const { list, loading } = useSelector((state) => state.interactions);

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  const handleDelete = (id) => {
    if (window.confirm(`Delete interaction #${id}?`)) {
      dispatch(deleteInteraction(id));
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return '#22c55e';
      case 'negative': return '#ef4444';
      default: return '#f59e0b';
    }
  };

  if (loading) {
    return (
      <div className="interactions-loading">
        <div className="spinner-small"></div>
        <p>Loading interactions...</p>
      </div>
    );
  }

  if (!list || list.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-icon">📭</span>
        <h3>No interactions yet</h3>
        <p>Use the AI assistant or the form to log your first HCP interaction.</p>
      </div>
    );
  }

  return (
    <div className="interactions-grid">
      {list.map((item) => (
        <div key={item.id} className="interaction-card">
          <div className="card-header">
            <div className="card-header-left">
              <span className="card-type-badge">{item.interaction_type || 'Meeting'}</span>
              <span className="card-date">{item.date || 'N/A'}</span>
            </div>
            <div className="card-header-right">
              {item.sentiment && (
                <span
                  className="sentiment-badge"
                  style={{ background: getSentimentColor(item.sentiment) + '18', color: getSentimentColor(item.sentiment) }}
                >
                  {item.sentiment}
                </span>
              )}
              <button className="btn-delete" onClick={() => handleDelete(item.id)} title="Delete">
                🗑️
              </button>
            </div>
          </div>
          <div className="card-body">
            <h3 className="card-hcp-name">{item.hcp_name || 'Unknown HCP'}</h3>
            {item.summary && <p className="card-summary">{item.summary}</p>}
            {item.topics_discussed && (
              <div className="card-field">
                <span className="field-label">Topics:</span>
                <span className="field-value">{item.topics_discussed}</span>
              </div>
            )}
            {item.outcomes && (
              <div className="card-field">
                <span className="field-label">Outcomes:</span>
                <span className="field-value">{item.outcomes}</span>
              </div>
            )}
            {item.products_discussed && item.products_discussed.length > 0 && (
              <div className="card-tags">
                {item.products_discussed.map((p, idx) => (
                  <span key={idx} className="tag">{p}</span>
                ))}
              </div>
            )}
            {item.follow_up_actions && item.follow_up_actions.length > 0 && (
              <div className="card-followups">
                <span className="field-label">Follow-ups:</span>
                <ul>
                  {item.follow_up_actions.map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="card-footer">
            <span className="card-id">#{item.id}</span>
            <span className="card-timestamp">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
