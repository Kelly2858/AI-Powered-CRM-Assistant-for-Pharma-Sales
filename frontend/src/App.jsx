import { useState } from 'react';
import { Provider } from 'react-redux';
import { store } from './store';
import Sidebar from './components/Sidebar';
import InteractionForm from './components/InteractionForm';
import ChatAssistant from './components/ChatAssistant';
import InteractionList from './components/InteractionList';
import './App.css';

function AppContent() {
  const [activePage, setActivePage] = useState('log');

  return (
    <div className="app-layout">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="main-content">
        {activePage === 'log' && (
          <>
            <header className="page-header">
              <h1>Log HCP Interaction</h1>
              <p className="page-subtitle">Use the AI assistant or fill the form manually</p>
            </header>
            <div className="split-panel">
              <InteractionForm />
              <ChatAssistant />
            </div>
          </>
        )}
        {activePage === 'interactions' && (
          <>
            <header className="page-header">
              <h1>Interaction History</h1>
              <p className="page-subtitle">All logged HCP interactions</p>
            </header>
            <InteractionList />
          </>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}
