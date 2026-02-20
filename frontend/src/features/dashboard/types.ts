/**
 * Types for the customizable dashboard widget system.
 */

import type React from 'react';

export interface LayoutItem {
  id: string;
  span: 1 | 2;
}

export interface WidgetDefinition {
  id: string;
  title: string;
  description: string;
  defaultSpan: 1 | 2;
  component: React.ComponentType;
}
