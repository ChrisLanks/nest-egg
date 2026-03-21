/**
 * Financial templates API client
 */

import api from "../services/api";

export interface TemplateInfo {
  id: string;
  category: "goal" | "rule" | "retirement" | "budget";
  name: string;
  description: string;
  is_activated: boolean;
}

export interface ActivateResult {
  status: string;
  template_id: string;
  message?: string;
}

export const financialTemplatesApi = {
  getAll: async (): Promise<TemplateInfo[]> => {
    const { data } = await api.get<TemplateInfo[]>("/financial-templates/");
    return data;
  },

  activate: async (templateId: string): Promise<ActivateResult> => {
    const { data } = await api.post<ActivateResult>(
      `/financial-templates/${templateId}/activate`,
    );
    return data;
  },
};
