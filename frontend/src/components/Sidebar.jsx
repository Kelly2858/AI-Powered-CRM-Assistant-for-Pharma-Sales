import { useState } from 'react';
import './Sidebar.css';

const navItems = [
  { id: 'log', icon: '➕', label: 'Log', title: 'Log Interaction' },
  { id: 'interactions', icon: '💬', label: 'History', title: 'Interaction History' },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">🧬</span>
        <span className="logo-text">CRM</span>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-btn ${activePage === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
            title={item.title}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="avatar">SR</div>
      </div>
    </aside>
  );
}
