import React from 'react';
import ReactDOM from 'react-dom/client';
import { ColorModeScript } from '@chakra-ui/react';
import App from './App.tsx';
import './index.css';
import { initializeMonitoring } from './services/monitoring';
import { theme } from './styles/theme';

// Initialize error tracking and monitoring
initializeMonitoring();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ColorModeScript initialColorMode={theme.config.initialColorMode} />
    <App />
  </React.StrictMode>
);
