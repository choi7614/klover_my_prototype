import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app';
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import './styles/globals.css';

const root = document.getElementById('root');
if (!root) throw new Error('앱을 표시할 영역을 찾을 수 없습니다.');

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
