/**
 * CSV import types and interfaces
 */

export interface CSVColumnMapping {
  date?: string;
  amount?: string;
  description?: string;
  merchant?: string;
}

export interface CSVPreviewRow {
  date: string | null;
  amount: number | null;
  description: string;
  merchant: string;
  raw: Record<string, string>;
}

export interface CSVPreviewResponse {
  headers: string[];
  detected_mapping: CSVColumnMapping;
  preview_rows: CSVPreviewRow[];
  total_rows: number;
}

export interface CSVImportRequest {
  account_id: string;
  column_mapping: CSVColumnMapping;
  skip_duplicates?: boolean;
}

export interface CSVImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
  total_processed: number;
}
