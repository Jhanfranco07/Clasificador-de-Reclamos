const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Error HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the generic message when the backend returns no JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export interface ClaimSummary {
  id: string;
  code: string;
  customerName: string;
  customerEmail: string;
  orderCode: string;
  channel: string;
  category: string;
  categoryKey: string;
  priority: string;
  priorityKey: string;
  status: string;
  statusKey: string;
  requiresHumanReview: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ClaimDetailResponse {
  claim: ClaimSummary & {
    description: string;
    orderDate?: string;
    responsible?: string;
    closedAt?: string;
    attentionMinutes?: number;
  };
  analysis: {
    id: string;
    category: string;
    categoryKey: string;
    confidence: number;
    sentiment: string;
    sentimentKey: string;
    keywords: string[];
    entities: string[];
    recommendation: string;
    model: string;
    createdAt: string;
  } | null;
  response: {
    id: string;
    suggestedResponse: string;
    editedResponse?: string;
    finalResponse?: string;
    status: string;
    createdAt: string;
    reviewedAt?: string;
  } | null;
  documents: Array<{
    id: string;
    title: string;
    type: string;
    category: string;
    score: number;
    fragment: string;
  }>;
  history: Array<{
    id: string;
    previousState?: string;
    newState: string;
    action: string;
    comment?: string;
    user?: string;
    createdAt: string;
  }>;
}

export interface DashboardResponse {
  metrics: Record<string, number>;
  byCategory: Array<{ categoria: string; total: number }>;
  byPriority: Array<{ prioridad: string; total: number }>;
  byStatus: Array<{ estado: string; total: number }>;
  recentClaims: ClaimSummary[];
}

export interface DocumentsResponse {
  items: Array<{
    id: string;
    title: string;
    type: string;
    category: string;
    content: string;
    indexStatus: string;
    updatedAt: string;
  }>;
  index: {
    fragmentos: number;
    documentos: number;
    vectorizador: boolean;
    matriz: boolean;
  };
}

export interface ConfigResponse {
  model: string;
  confidenceThreshold: number;
  humanReviewRequired: boolean;
  useRag: boolean;
  maxDocuments: number;
  updatedAt?: string;
}

export interface ReportsResponse extends DashboardResponse {
  confidenceByCategory: Array<{ categoria: string; confianza_promedio: number; total: number }>;
  responsesByReviewStatus: Array<{ estado_revision: string; total: number }>;
  attentionTimeByCategory: Array<{ categoria: string; tiempo_promedio_min: number; total: number }>;
}

export function listClaims() {
  return request<{ items: ClaimSummary[] }>('/api/claims');
}

export function getClaim(id: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}`);
}

export function createClaim(payload: {
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  order_code: string;
  channel: string;
  order_date?: string;
  description: string;
  analyze: boolean;
}) {
  return request<ClaimDetailResponse>('/api/claims', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function analyzeClaim(id: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}/analyze`, { method: 'POST' });
}

export function updateClaimState(id: string, state: string, comment?: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}/state`, {
    method: 'PATCH',
    body: JSON.stringify({ state, comment }),
  });
}

export function updateResponse(id: string, responseText: string) {
  return request<ClaimDetailResponse>(`/api/responses/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ response_text: responseText }),
  });
}

export function approveResponse(id: string, responseText: string) {
  return request<ClaimDetailResponse>(`/api/responses/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ response_text: responseText }),
  });
}

export function getDashboard() {
  return request<DashboardResponse>('/api/dashboard');
}

export function getDocuments() {
  return request<DocumentsResponse>('/api/documents');
}

export function reindexDocuments() {
  return request<Record<string, unknown>>('/api/documents/reindex', { method: 'POST' });
}

export function getConfig() {
  return request<ConfigResponse>('/api/config');
}

export function saveConfig(payload: {
  confidence_threshold: number;
  human_review_required: boolean;
  use_rag: boolean;
  max_documents: number;
}) {
  return request<ConfigResponse>('/api/config', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function getReports() {
  return request<ReportsResponse>('/api/reports');
}
