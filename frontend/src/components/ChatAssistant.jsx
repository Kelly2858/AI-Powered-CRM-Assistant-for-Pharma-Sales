import { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { sendMessage, addMessage, clearChat } from '../store/slices/chatSlice';
import { fetchInteractions, updateFormData } from '../store/slices/interactionSlice';
import './ChatAssistant.css';

export default function ChatAssistant() {
  const [input, setInput] = useState('');
  const dispatch = useDispatch();
  const { messages, loading } = useSelector((state) => state.chat);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    
    // Auto-fill form from AI response
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === 'assistant') {
        const match = lastMsg.content.match(/<FormFill>([\s\S]*?)<\/FormFill>/);
        if (match) {
          try {
            const data = JSON.parse(match[1]);
            dispatch(updateFormData(data));
          } catch(e) { console.error("Parse error", e); }
        }
      }
    }
  }, [messages, dispatch]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');

    dispatch(addMessage({ role: 'user', content: userMessage }));

    const chatHistory = messages
      .filter((m) => m.role !== 'system')
      .map((m) => ({ role: m.role, content: m.content }));

    await dispatch(sendMessage({ message: userMessage, chatHistory }));
    
    // Refresh interactions list after AI response
    setTimeout(() => {
      dispatch(fetchInteractions());
    }, 1000);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatContent = (content) => {
    // Hide FormFill tags from UI
    let displayContent = content.replace(/<FormFill>[\s\S]*?<\/FormFill>/g, '').trim();
    // Simple markdown-like formatting
    return displayContent
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>')
      .replace(/- (.*?)(?=<br\/>|$)/g, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-bot-icon">🤖</span>
          <h2>AI Assistant</h2>
          <span className={`status-dot ${loading ? 'processing' : 'online'}`}></span>
        </div>
        <button className="btn-clear-chat" onClick={() => dispatch(clearChat())} title="Clear chat">
          🗑️
        </button>
      </div>

      <div className="chat-input-area top-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your interaction..."
          rows={2}
          disabled={loading}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          title="Send"
        >
          {loading ? '⏳' : '📤'}
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`chat-msg ${msg.role} ${msg.content && msg.content.includes('<FormFill>') ? 'success-msg' : ''}`}>
            <div className="msg-avatar">
              {msg.role === 'assistant' ? '🤖' : '👤'}
            </div>
            <div
              className="msg-content"
              dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }}
            />
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="msg-avatar">🤖</div>
            <div className="msg-content">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
