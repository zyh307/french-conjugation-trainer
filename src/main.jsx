import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';
import './compact.css';

class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="fatal-screen"><div className="brand-mark">ç</div><h1>界面暂时遇到了一点问题</h1><p>学习进度已经保存在本机，刷新后可以继续。</p><button className="button primary" onClick={() => window.location.reload()}>重新打开</button></div> : this.props.children;
  }
}

createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
