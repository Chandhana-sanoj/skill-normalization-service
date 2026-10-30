import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '40px', fontFamily: 'sans-serif', color: '#7a3520', background: '#fff8f5', minHeight: '100vh' }}>
          <h2>Something went wrong</h2>
          <pre style={{ background: '#fff0eb', padding: '16px', borderRadius: '8px', overflow: 'auto', fontSize: '13px', whiteSpace: 'pre-wrap' }}>
            {this.state.error.toString()}
            {this.state.error.stack ? '\n\n' + this.state.error.stack : ''}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: '16px', padding: '8px 20px', cursor: 'pointer', borderRadius: '6px', border: '1px solid #d97048', background: '#d97048', color: '#fff', fontSize: '14px' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </StrictMode>,
)
