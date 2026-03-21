import React from "react";
import ReactDOM from "react-dom/client";
import { ColorModeScript } from "@chakra-ui/react";
import App from "./App.tsx";
import "./index.css";
import { initializeMonitoring } from "./services/monitoring";
import { theme } from "./styles/theme";

// Initialize error tracking and monitoring
initializeMonitoring();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ColorModeScript initialColorMode={theme.config.initialColorMode} />
    <App />
  </React.StrictMode>,
);

// Register service worker for PWA support
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Service worker registration failed — app still works without it
    });
  });
}
