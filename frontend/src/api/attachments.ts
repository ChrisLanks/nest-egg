/**
 * Transaction Attachments API client
 */

import api from "../services/api";

export interface Attachment {
  id: string;
  transaction_id: string;
  filename: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  created_at: string;
}

export const attachmentsApi = {
  list: async (
    transactionId: string,
  ): Promise<{ attachments: Attachment[] }> => {
    const { data } = await api.get(
      `/attachments/transactions/${transactionId}/attachments`,
    );
    return data;
  },

  upload: async (transactionId: string, file: File): Promise<Attachment> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post(
      `/attachments/transactions/${transactionId}/attachments`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return data;
  },

  download: (attachmentId: string): string => {
    return `${api.defaults.baseURL}/attachments/attachments/${attachmentId}/download`;
  },

  delete: async (attachmentId: string): Promise<void> => {
    await api.delete(`/attachments/attachments/${attachmentId}`);
  },
};
