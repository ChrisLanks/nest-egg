/**
 * CSV Import API client
 */

import api from '../services/api';
import type { CSVPreviewResponse, CSVImportResponse, CSVColumnMapping } from '../types/csv-import';

export const csvImportApi = {
  /**
   * Validate CSV file format
   */
  validate: async (file: File): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post<{ message: string }>('/csv-import/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  /**
   * Preview CSV file before import
   */
  preview: async (file: File, columnMapping?: CSVColumnMapping): Promise<CSVPreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (columnMapping) {
      formData.append('column_mapping', JSON.stringify(columnMapping));
    }

    const { data } = await api.post<CSVPreviewResponse>('/csv-import/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  /**
   * Import transactions from CSV
   */
  import: async (
    accountId: string,
    file: File,
    columnMapping: CSVColumnMapping,
    skipDuplicates: boolean = true
  ): Promise<CSVImportResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    // Use query params instead of formData for non-file data
    const params = new URLSearchParams({
      account_id: accountId,
      skip_duplicates: skipDuplicates.toString(),
    });

    // Add column mapping as query param
    if (columnMapping) {
      params.append('column_mapping', JSON.stringify(columnMapping));
    }

    const { data } = await api.post<CSVImportResponse>(
      `/csv-import/import?${params.toString()}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return data;
  },
};
