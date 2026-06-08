const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'smartclaim_token';
const REQUEST_TIMEOUT_MS = 30_000;

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  options.signal?.addEventListener('abort', () => controller.abort(), { once: true });
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('La solicitud tardó demasiado. Intenta nuevamente.');
    }
    throw new Error('No se pudo conectar con el servidor. Verifica que la API esté activa y vuelve a intentarlo.');
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    let message = `Error HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the generic message when the backend returns no JSON.
    }
    if (response.status === 401 && token) {
      clearStoredToken();
      window.dispatchEvent(new Event('smartclaim:unauthorized'));
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

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: 'CLIENT' | 'AGENT' | 'ADMIN';
  phone?: string;
  createdAt: string;
}

export interface AuthResponse {
  user: AuthUser;
  token: string;
}

export interface ApiOrderItem {
  id: string;
  name: string;
  quantity: number;
  price: number;
  image?: string;
}

export interface ApiOrder {
  id: string;
  code: string;
  userId: string;
  storeName: string;
  storeImage?: string;
  status: 'DELIVERED' | 'IN_TRANSIT' | 'CANCELLED' | 'DELAYED' | 'PREPARING';
  total: number;
  paymentMethod: string;
  deliveryAddress: string;
  deliveryDriver?: string;
  items: ApiOrderItem[];
  createdAt: string;
  estimatedDelivery?: string;
}

export interface CatalogProduct {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
}

export interface CatalogRestaurant {
  id: string;
  name: string;
  category: string;
  rating: number;
  time: string;
  delivery: number;
  image: string;
  products: CatalogProduct[];
}

export interface NotificationItem {
  id: string;
  claimId?: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  createdAt: string;
}

export interface ClaimMessage {
  id: string;
  claimId: string;
  senderType: 'client' | 'agent' | 'ai' | 'system';
  senderId?: string;
  message: string;
  isInternal: boolean;
  createdAt: string;
  readAt?: string;
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

export interface AgentCommentsResponse {
  items: Array<{
    id: string;
    claimId: string;
    comment: string;
    type: string;
    user: string;
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
    provider?: string;
    modelo_embedding?: string;
    embeddings?: number;
  };
}

export interface ReindexResponse {
  status: string;
  provider?: string;
  fragmentos?: number;
  modelo_embedding?: string;
  fallback_reason?: string;
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
  firstResponseTimeByCategory: Array<{ categoria: string; tiempo_promedio_min: number; total: number }>;
  claimsEvolution: Array<{ fecha: string; total: number }>;
  filters?: Record<string, string | null>;
}

export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export async function loginUser(email: string, password: string) {
  const result = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setStoredToken(result.token);
  return result;
}

export async function registerUser(payload: { name: string; email: string; phone?: string; password: string }) {
  const result = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  setStoredToken(result.token);
  return result;
}

export function requestPasswordReset(email: string) {
  return request<{ ok: boolean; message: string }>('/api/auth/password-reset/request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function getMe() {
  return request<{ user: AuthUser }>('/api/auth/me');
}

export function updateMe(payload: { name: string; phone?: string }) {
  return request<{ user: AuthUser }>('/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function getCatalog() {
  return request<{ items: CatalogRestaurant[] }>('/api/catalog');
}

export function listNotifications() {
  return request<{ items: NotificationItem[]; unread: number }>('/api/notifications');
}

export function markNotificationsRead() {
  return request<{ items: NotificationItem[]; unread: number }>('/api/notifications/read', {
    method: 'PATCH',
  });
}

export function listOrders() {
  return request<{ items: ApiOrder[] }>('/api/orders');
}

export function getOrder(id: string) {
  return request<{ order: ApiOrder }>(`/api/orders/${id}`);
}

export function createOrder(payload: {
  store_name: string;
  store_image?: string;
  payment_method: string;
  delivery_address: string;
  items: Array<{ name: string; quantity: number; price: number; image?: string }>;
}) {
  return request<{ order: ApiOrder }>('/api/orders', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listClaims(filters: {
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);
  if (filters.status && filters.status !== 'ALL') params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  params.set('page', String(filters.page || 1));
  params.set('page_size', String(filters.pageSize || 10));
  return request<{ items: ClaimSummary[]; pagination: Pagination }>(`/api/claims?${params}`);
}

export function getClaim(id: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}`);
}

export function listClaimMessages(id: string) {
  return request<{ items: ClaimMessage[] }>(`/api/claims/${id}/messages`);
}

export function sendClaimMessage(id: string, message: string) {
  return request<{ items: ClaimMessage[] }>(`/api/claims/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function closeClaim(id: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}/close`, { method: 'POST' });
}

export function reopenClaim(id: string) {
  return request<ClaimDetailResponse>(`/api/claims/${id}/reopen`, { method: 'POST' });
}

export function sendChatMessage(message: string, sessionId?: string, context?: Record<string, unknown>) {
  return request<{ message: string; documents: string[]; provider: string }>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId, context }),
  });
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

export function listAgentComments(id: string) {
  return request<AgentCommentsResponse>(`/api/claims/${id}/comments`);
}

export function createAgentComment(id: string, comment: string, type = 'INTERNO') {
  return request<AgentCommentsResponse>(`/api/claims/${id}/comments`, {
    method: 'POST',
    body: JSON.stringify({ comment, type }),
  });
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
  return request<ReindexResponse>('/api/documents/reindex', { method: 'POST' });
}

export function createDocument(payload: { title: string; type: string; category: string; content: string }) {
  return request<DocumentsResponse>('/api/documents', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateDocument(id: string, payload: { title: string; type: string; category: string; content: string }) {
  return request<DocumentsResponse>(`/api/documents/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteDocument(id: string) {
  return request<DocumentsResponse>(`/api/documents/${id}`, {
    method: 'DELETE',
  });
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

export function getReports(filters: {
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  category?: string;
  priority?: string;
} = {}) {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);
  if (filters.status && filters.status !== 'ALL') params.set('status', filters.status);
  if (filters.category && filters.category !== 'ALL') params.set('category', filters.category);
  if (filters.priority && filters.priority !== 'ALL') params.set('priority', filters.priority);
  return request<ReportsResponse>(`/api/reports?${params}`);
}
