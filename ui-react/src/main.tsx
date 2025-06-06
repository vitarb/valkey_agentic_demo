import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import TopicPage from './TopicPage';
import './index.css';

function Root() {
  const path = window.location.pathname;
  if (path.startsWith('/topic/')) {
    const slug = path.split('/')[2] || '';
    return <TopicPage slug={slug} />;
  }
  const uid = path.startsWith('/user/') ? path.split('/')[2] : undefined;
  return <App initialUid={uid} />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
