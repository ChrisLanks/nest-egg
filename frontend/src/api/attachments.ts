/**
 * Transaction Attachments API client
 */

import api from "../services/api";

export interface OcrData {
  merchant: string | null;
  amount: string | null;
  date: string | null;
  raw_text: string | null;
  confidence: number;
}

export interface Attachment {
  id: string;
  transaction_id: string;
  filename: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  created_at: string;
  ocr_status?: string | null;
  ocr_data?: OcrData | null;
}

export const attachmentsApi = {
  list: async (
    transactionId: string,
  ): Promise<{ attachments: Attachment[] }> => {
    const { data } = await api.get(
      `/transactions/${transactionId}/attachments`,
    );
    return data;
  },

  upload: async (transactionId: string, file: File): Promise<Attachment> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post(
      `/transactions/${transactionId}/attachments`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return data;
  },

  download: (attachmentId: string): string => {
    return `${api.defaults.baseURL}/attachments/${attachmentId}/download`;
  },

  delete: async (attachmentId: string): Promise<void> => {
    await api.delete(`/attachments/${attachmentId}`);
  },
};
