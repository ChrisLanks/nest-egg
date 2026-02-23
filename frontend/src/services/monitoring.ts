/**
 * Monitoring and error tracking configuration
 *
 * To enable Sentry:
 * 1. Install: npm install @sentry/react
 * 2. Set VITE_SENTRY_DSN in .env.production
 * 3. Uncomment the Sentry initialization code below
 */

// import * as Sentry from '@sentry/react';

/**
 * Initialize error tracking and monitoring
 */
export function initializeMonitoring() {
  // Only enable monitoring in production
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when ready to use Sentry:

    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,

      // Performance monitoring
      integrations: [
        new Sentry.BrowserTracing({
          // Track navigation between pages
          routingInstrumentation: Sentry.reactRouterV6Instrumentation(
            React.useEffect,
            useLocation,
            useNavigationType,
            createRoutesFromChildren,
            matchRoutes
          ),
        }),
        // Session replay for debugging
        new Sentry.Replay({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],

      // Performance monitoring sample rate (10% of transactions)
      tracesSampleRate: 0.1,

      // Session replay sample rates
      replaysSessionSampleRate: 0.1, // 10% of sessions
      replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors

      // Environment and release tracking
      environment: import.meta.env.MODE,
      release: import.meta.env.VITE_APP_VERSION || 'development',

      // Filter out sensitive data
      beforeSend(event, hint) {
        // Remove sensitive data from breadcrumbs
        if (event.breadcrumbs) {
          event.breadcrumbs = event.breadcrumbs.map(breadcrumb => {
            if (breadcrumb.data) {
              // Remove tokens and passwords
              const { authorization, password, token, ...safeData } = breadcrumb.data;
              return { ...breadcrumb, data: safeData };
            }
            return breadcrumb;
          });
        }

        // Remove sensitive headers
        if (event.request?.headers) {
          const { authorization, cookie, ...safeHeaders } = event.request.headers;
          event.request.headers = safeHeaders;
        }

        return event;
      },

      // Ignore certain errors
      ignoreErrors: [
        // Browser extensions
        'top.GLOBALS',
        // Network errors
        'NetworkError',
        'Failed to fetch',
        // User cancelled actions
        'AbortError',
      ],
    });

    console.info('Sentry monitoring initialized');
    */
  }

  // Custom error handler for development
  if (import.meta.env.DEV) {
    window.addEventListener('error', (event) => {
      console.error('Global error:', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error,
      });
    });

    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', {
        reason: event.reason,
        promise: event.promise,
      });
    });
  }
}

/**
 * Log a custom event to monitoring service
 */
export function logEvent(eventName: string, data?: Record<string, any>) {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when Sentry is enabled:
    Sentry.captureEvent({
      message: eventName,
      level: 'info',
      extra: data,
    });
    */
  } else if (import.meta.env.DEV) {
    console.log(`[Event] ${eventName}`, data);
  }
}

/**
 * Log an error to monitoring service
 */
export function logError(error: Error, context?: Record<string, any>) {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when Sentry is enabled:
    Sentry.captureException(error, {
      extra: context,
    });
    */
  }

  // Always log to console
  console.error('Error:', error, context);
}

/**
 * Set user context for error tracking
 */
export function setUserContext(_user: { id: string; email: string; name?: string }) {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when Sentry is enabled:
    Sentry.setUser({
      id: user.id,
      email: user.email,
      username: user.name,
    });
    */
  }
}

/**
 * Clear user context (on logout)
 */
export function clearUserContext() {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when Sentry is enabled:
    Sentry.setUser(null);
    */
  }
}

/**
 * Add breadcrumb for debugging
 */
export function addBreadcrumb(message: string, data?: Record<string, any>) {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    /* Uncomment when Sentry is enabled:
    Sentry.addBreadcrumb({
      message,
      data,
      level: 'info',
    });
    */
  } else if (import.meta.env.DEV) {
    console.debug(`[Breadcrumb] ${message}`, data);
  }
}
