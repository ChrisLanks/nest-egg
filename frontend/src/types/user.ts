/**
 * User and Organization types
 */

export interface User {
  id: string;
  organization_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  is_active: boolean;
  is_org_admin: boolean;
  email_verified: boolean;
  dashboard_layout?: Array<{ id: string; span: 1 | 2 }> | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  custom_month_end_day: number;
  timezone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
