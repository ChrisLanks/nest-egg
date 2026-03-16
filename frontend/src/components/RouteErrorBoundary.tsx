/**
 * Per-route error boundary that catches errors within individual pages.
 *
 * Unlike the root ErrorBoundary (which requires a full page reload),
 * this one lets users navigate away from the broken page.
 */

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error(
      "[RouteErrorBoundary] Caught error:",
      error,
      info.componentStack,
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "50vh",
            gap: "16px",
            fontFamily: "sans-serif",
            color: "var(--chakra-colors-chakra-body-text)",
            padding: "32px",
          }}
        >
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600 }}>
            This page encountered an error
          </h2>
          <p
            style={{
              opacity: 0.7,
              fontSize: "0.875rem",
              maxWidth: "400px",
              textAlign: "center",
            }}
          >
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={() =>
                this.setState({ hasError: false, error: undefined })
              }
              style={{
                padding: "8px 20px",
                background: "#3f9142",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.875rem",
              }}
            >
              Try Again
            </button>
            <button
              onClick={() => (window.location.href = "/overview")}
              style={{
                padding: "8px 20px",
                background: "transparent",
                color: "var(--chakra-colors-chakra-body-text)",
                border: "1px solid currentColor",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.875rem",
                opacity: 0.7,
              }}
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
