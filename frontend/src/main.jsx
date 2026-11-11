import { StrictMode, Component, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Lazily load the Super Admin app only when navigating to /super-admin/*
// This keeps the org-app bundle unaffected by the SA code.
const SuperAdminApp = lazy(() => import('./superadmin/SuperAdminApp.jsx'))

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

// Route detection: pathname determines which app to render.
// The Super Admin app uses hash routing internally (#/super-admin/...).
// The org app does not use the URL at all (session state only).
// We detect by both pathname AND hash to cover direct navigation.
function isSuperAdminRoute() {
  const path = window.location.pathname;
  const hash = window.location.hash;
  return (
    path.startsWith('/super-admin') ||
    hash.startsWith('#/super-admin')
  );
}

function Root() {
  // Static check at mount — the page will reload on hard navigation anyway.
  // For SPA in-page navigation the SuperAdminApp manages its own hash routes.
  if (isSuperAdminRoute()) {
    return (
      <Suspense fallback={<div style={{ padding: 40, fontFamily: 'sans-serif', color: '#7a3520' }}>Loading…</div>}>
        <SuperAdminApp />
      </Suspense>
    );
  }
  return <App />;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppErrorBoundary>
      <Root />
    </AppErrorBoundary>
  </StrictMode>,
)
