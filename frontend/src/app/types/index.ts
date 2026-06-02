// Types for SmartClaim AI System

export type UserRole = 'CLIENT' | 'AGENT' | 'ADMIN';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  avatar?: string;
  createdAt: Date;
}

export type OrderStatus = 'DELIVERED' | 'IN_TRANSIT' | 'CANCELLED' | 'DELAYED' | 'PREPARING';

export interface Order {
  id: string;
  code: string;
  userId: string;
  storeName: string;
  storeImage?: string;
  status: OrderStatus;
  total: number;
  paymentMethod: string;
  deliveryAddress: string;
  deliveryDriver?: string;
  items: OrderItem[];
  createdAt: Date;
  estimatedDelivery?: Date;
}

export interface OrderItem {
  id: string;
  name: string;
  quantity: number;
  price: number;
  image?: string;
}

export type ClaimStatus = 'RECEIVED' | 'ANALYZING' | 'IN_REVIEW' | 'RESPONDED' | 'ESCALATED' | 'CLOSED';
export type ClaimCategory = 'INCORRECT_CHARGE' | 'DELAY' | 'WRONG_PRODUCT' | 'CARD_ISSUE' | 'FRAUD' | 'GENERAL_SUPPORT';
export type ClaimPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Claim {
  id: string;
  code: string;
  userId: string;
  orderId: string;
  description: string;
  customerSelectedType: ClaimCategory;
  detectedCategory?: ClaimCategory;
  confidence?: number;
  priority: ClaimPriority;
  status: ClaimStatus;
  sentiment?: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' | 'URGENT';
  requiresHumanReview: boolean;
  createdAt: Date;
  updatedAt: Date;
  channel: 'WEB' | 'MOBILE' | 'EMAIL' | 'PHONE';
}

export interface ClaimAnalysis {
  id: string;
  claimId: string;
  category: ClaimCategory;
  confidence: number;
  priority: ClaimPriority;
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' | 'URGENT';
  requiresHumanReview: boolean;
  retrievedDocuments: string[];
  createdAt: Date;
}

export interface ClaimResponse {
  id: string;
  claimId: string;
  suggestedResponse: string;
  finalResponse?: string;
  status: 'PENDING' | 'APPROVED' | 'EDITED' | 'REJECTED';
  reviewedBy?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ClaimHistoryEvent {
  id: string;
  claimId: string;
  action: string;
  description: string;
  performedBy?: string;
  createdAt: Date;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  type: 'POLICY' | 'FAQ' | 'PROCEDURE' | 'MANUAL';
  content: string;
  category: string;
  indexed: boolean;
  updatedAt: Date;
}

export const CLAIM_CATEGORY_LABELS: Record<ClaimCategory, string> = {
  INCORRECT_CHARGE: 'Cobro indebido',
  DELAY: 'Retraso en pedido',
  WRONG_PRODUCT: 'Producto incorrecto',
  CARD_ISSUE: 'Problema con tarjeta',
  FRAUD: 'Fraude o seguridad',
  GENERAL_SUPPORT: 'Soporte general'
};

export const CLAIM_STATUS_LABELS: Record<ClaimStatus, string> = {
  RECEIVED: 'Recibido',
  ANALYZING: 'En análisis',
  IN_REVIEW: 'En revisión',
  RESPONDED: 'Respondido',
  ESCALATED: 'Escalado',
  CLOSED: 'Cerrado'
};

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  DELIVERED: 'Entregado',
  IN_TRANSIT: 'En camino',
  CANCELLED: 'Cancelado',
  DELAYED: 'Con demora',
  PREPARING: 'Preparando'
};
