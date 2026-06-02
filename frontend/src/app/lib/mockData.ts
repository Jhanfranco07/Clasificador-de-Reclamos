import { User, Order, Claim, ClaimAnalysis, ClaimResponse, ClaimHistoryEvent, KnowledgeDocument } from '../types';

// Mock Users
export const mockUsers: User[] = [
  {
    id: 'user-1',
    name: 'María González',
    email: 'maria.gonzalez@email.com',
    role: 'CLIENT',
    phone: '+34 612 345 678',
    createdAt: new Date('2024-01-15')
  },
  {
    id: 'user-2',
    name: 'Carlos Rodríguez',
    email: 'carlos.rodriguez@email.com',
    role: 'CLIENT',
    phone: '+34 623 456 789',
    createdAt: new Date('2024-02-20')
  },
  {
    id: 'agent-1',
    name: 'Laura Martínez',
    email: 'laura.martinez@smartclaim.com',
    role: 'AGENT',
    createdAt: new Date('2023-06-10')
  },
  {
    id: 'admin-1',
    name: 'Admin System',
    email: 'admin@smartclaim.com',
    role: 'ADMIN',
    createdAt: new Date('2023-01-01')
  }
];

// Mock Orders
export const mockOrders: Order[] = [
  {
    id: 'order-1',
    code: 'ORD-2024-001',
    userId: 'user-1',
    storeName: 'Burger Palace',
    storeImage: 'https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=200',
    status: 'DELIVERED',
    total: 24.50,
    paymentMethod: 'Tarjeta de crédito',
    deliveryAddress: 'Calle Mayor 123, 28013 Madrid',
    deliveryDriver: 'Juan Pérez',
    items: [
      { id: 'item-1', name: 'Hamburguesa Clásica', quantity: 2, price: 8.50 },
      { id: 'item-2', name: 'Papas Fritas', quantity: 1, price: 3.50 },
      { id: 'item-3', name: 'Refresco Cola', quantity: 2, price: 2.00 }
    ],
    createdAt: new Date('2024-06-01T18:30:00'),
    estimatedDelivery: new Date('2024-06-01T19:15:00')
  },
  {
    id: 'order-2',
    code: 'ORD-2024-002',
    userId: 'user-1',
    storeName: 'Sushi Express',
    storeImage: 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=200',
    status: 'DELAYED',
    total: 45.80,
    paymentMethod: 'PayPal',
    deliveryAddress: 'Calle Mayor 123, 28013 Madrid',
    deliveryDriver: 'Ana López',
    items: [
      { id: 'item-4', name: 'Roll California', quantity: 2, price: 12.90 },
      { id: 'item-5', name: 'Roll Tempura', quantity: 1, price: 14.50 },
      { id: 'item-6', name: 'Sopa Miso', quantity: 2, price: 2.75 }
    ],
    createdAt: new Date('2024-06-02T13:00:00'),
    estimatedDelivery: new Date('2024-06-02T14:00:00')
  },
  {
    id: 'order-3',
    code: 'ORD-2024-003',
    userId: 'user-1',
    storeName: 'Pizza Napoli',
    storeImage: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=200',
    status: 'IN_TRANSIT',
    total: 32.00,
    paymentMethod: 'Tarjeta de débito',
    deliveryAddress: 'Calle Mayor 123, 28013 Madrid',
    deliveryDriver: 'Pedro Sánchez',
    items: [
      { id: 'item-7', name: 'Pizza Margarita', quantity: 1, price: 12.00 },
      { id: 'item-8', name: 'Pizza Pepperoni', quantity: 1, price: 14.00 },
      { id: 'item-9', name: 'Agua Mineral', quantity: 2, price: 3.00 }
    ],
    createdAt: new Date('2024-06-02T19:45:00'),
    estimatedDelivery: new Date('2024-06-02T20:30:00')
  },
  {
    id: 'order-4',
    code: 'ORD-2024-004',
    userId: 'user-2',
    storeName: 'Taco Loco',
    storeImage: 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=200',
    status: 'DELIVERED',
    total: 28.50,
    paymentMethod: 'Efectivo',
    deliveryAddress: 'Avenida Diagonal 456, 08029 Barcelona',
    deliveryDriver: 'Miguel Torres',
    items: [
      { id: 'item-10', name: 'Tacos al Pastor', quantity: 3, price: 7.50 },
      { id: 'item-11', name: 'Nachos con Queso', quantity: 1, price: 6.00 }
    ],
    createdAt: new Date('2024-05-30T20:00:00'),
    estimatedDelivery: new Date('2024-05-30T20:45:00')
  }
];

// Mock Claims
export const mockClaims: Claim[] = [
  {
    id: 'claim-1',
    code: 'CLM-2024-001',
    userId: 'user-1',
    orderId: 'order-1',
    description: 'Me cobraron dos veces el mismo pedido en mi tarjeta de crédito. Vi dos cargos de 24.50€ en mi cuenta.',
    customerSelectedType: 'INCORRECT_CHARGE',
    detectedCategory: 'INCORRECT_CHARGE',
    confidence: 0.95,
    priority: 'HIGH',
    status: 'RESPONDED',
    sentiment: 'NEGATIVE',
    requiresHumanReview: true,
    createdAt: new Date('2024-06-01T19:30:00'),
    updatedAt: new Date('2024-06-01T20:15:00'),
    channel: 'WEB'
  },
  {
    id: 'claim-2',
    code: 'CLM-2024-002',
    userId: 'user-1',
    orderId: 'order-2',
    description: 'El pedido lleva más de 1 hora de retraso. La aplicación dice que está en camino pero no llega.',
    customerSelectedType: 'DELAY',
    detectedCategory: 'DELAY',
    confidence: 0.92,
    priority: 'MEDIUM',
    status: 'IN_REVIEW',
    sentiment: 'NEGATIVE',
    requiresHumanReview: false,
    createdAt: new Date('2024-06-02T14:30:00'),
    updatedAt: new Date('2024-06-02T14:45:00'),
    channel: 'WEB'
  },
  {
    id: 'claim-3',
    code: 'CLM-2024-003',
    userId: 'user-2',
    orderId: 'order-4',
    description: 'Pedí tacos sin cebolla por alergia y me los trajeron con cebolla. Esto es peligroso para mi salud.',
    customerSelectedType: 'WRONG_PRODUCT',
    detectedCategory: 'WRONG_PRODUCT',
    confidence: 0.88,
    priority: 'HIGH',
    status: 'ANALYZING',
    sentiment: 'URGENT',
    requiresHumanReview: true,
    createdAt: new Date('2024-06-02T20:50:00'),
    updatedAt: new Date('2024-06-02T20:50:00'),
    channel: 'MOBILE'
  },
  {
    id: 'claim-4',
    code: 'CLM-2024-004',
    userId: 'user-1',
    orderId: 'order-3',
    description: '¿Cómo puedo cambiar mi método de pago predeterminado?',
    customerSelectedType: 'GENERAL_SUPPORT',
    detectedCategory: 'GENERAL_SUPPORT',
    confidence: 0.75,
    priority: 'LOW',
    status: 'RECEIVED',
    sentiment: 'NEUTRAL',
    requiresHumanReview: false,
    createdAt: new Date('2024-06-02T19:50:00'),
    updatedAt: new Date('2024-06-02T19:50:00'),
    channel: 'WEB'
  }
];

// Mock Claim Analyses
export const mockClaimAnalyses: ClaimAnalysis[] = [
  {
    id: 'analysis-1',
    claimId: 'claim-1',
    category: 'INCORRECT_CHARGE',
    confidence: 0.95,
    priority: 'HIGH',
    sentiment: 'NEGATIVE',
    requiresHumanReview: true,
    retrievedDocuments: ['doc-1', 'doc-3'],
    createdAt: new Date('2024-06-01T19:31:00')
  },
  {
    id: 'analysis-2',
    claimId: 'claim-2',
    category: 'DELAY',
    confidence: 0.92,
    priority: 'MEDIUM',
    sentiment: 'NEGATIVE',
    requiresHumanReview: false,
    retrievedDocuments: ['doc-2', 'doc-5'],
    createdAt: new Date('2024-06-02T14:31:00')
  },
  {
    id: 'analysis-3',
    claimId: 'claim-3',
    category: 'WRONG_PRODUCT',
    confidence: 0.88,
    priority: 'HIGH',
    sentiment: 'URGENT',
    requiresHumanReview: true,
    retrievedDocuments: ['doc-4', 'doc-6'],
    createdAt: new Date('2024-06-02T20:51:00')
  }
];

// Mock Claim Responses
export const mockClaimResponses: ClaimResponse[] = [
  {
    id: 'response-1',
    claimId: 'claim-1',
    suggestedResponse: 'Estimada María, lamentamos mucho el inconveniente. Hemos verificado el cargo duplicado en su cuenta. Procederemos a realizar el reembolso de 24.50€ inmediatamente. El dinero estará disponible en su cuenta en 3-5 días hábiles. Como compensación, le hemos agregado un cupón de 10€ para su próximo pedido.',
    finalResponse: 'Estimada María, lamentamos mucho el inconveniente causado por el cargo duplicado. Hemos verificado la incidencia y confirmo que procederemos inmediatamente con el reembolso de 24.50€. El importe estará disponible en su cuenta en un plazo de 3-5 días hábiles. Adicionalmente, como gesto de disculpa, hemos añadido un cupón de 10€ a su cuenta para su próximo pedido. Gracias por su paciencia y comprensión.',
    status: 'EDITED',
    reviewedBy: 'agent-1',
    createdAt: new Date('2024-06-01T19:35:00'),
    updatedAt: new Date('2024-06-01T20:15:00')
  },
  {
    id: 'response-2',
    claimId: 'claim-2',
    suggestedResponse: 'Estimada María, entendemos su frustración por el retraso. Hemos contactado con el repartidor y su pedido llegará en aproximadamente 15 minutos. Le ofrecemos un descuento del 20% en este pedido como compensación por el tiempo de espera.',
    status: 'PENDING',
    createdAt: new Date('2024-06-02T14:35:00'),
    updatedAt: new Date('2024-06-02T14:35:00')
  }
];

// Mock Claim History
export const mockClaimHistory: ClaimHistoryEvent[] = [
  {
    id: 'hist-1',
    claimId: 'claim-1',
    action: 'CLAIM_CREATED',
    description: 'Reclamo recibido del cliente',
    createdAt: new Date('2024-06-01T19:30:00')
  },
  {
    id: 'hist-2',
    claimId: 'claim-1',
    action: 'AI_ANALYSIS',
    description: 'Sistema inteligente analizó el reclamo',
    createdAt: new Date('2024-06-01T19:31:00')
  },
  {
    id: 'hist-3',
    claimId: 'claim-1',
    action: 'HUMAN_REVIEW',
    description: 'Reclamo asignado a agente para revisión',
    performedBy: 'agent-1',
    createdAt: new Date('2024-06-01T19:35:00')
  },
  {
    id: 'hist-4',
    claimId: 'claim-1',
    action: 'RESPONSE_SENT',
    description: 'Respuesta enviada al cliente',
    performedBy: 'agent-1',
    createdAt: new Date('2024-06-01T20:15:00')
  },
  {
    id: 'hist-5',
    claimId: 'claim-2',
    action: 'CLAIM_CREATED',
    description: 'Reclamo recibido del cliente',
    createdAt: new Date('2024-06-02T14:30:00')
  },
  {
    id: 'hist-6',
    claimId: 'claim-2',
    action: 'AI_ANALYSIS',
    description: 'Sistema inteligente analizó el reclamo',
    createdAt: new Date('2024-06-02T14:31:00')
  }
];

// Mock Knowledge Documents
export const mockKnowledgeDocuments: KnowledgeDocument[] = [
  {
    id: 'doc-1',
    title: 'Política de Reembolsos por Cargos Duplicados',
    type: 'POLICY',
    content: 'En caso de cargos duplicados verificados, proceder con reembolso inmediato. Tiempo de procesamiento: 3-5 días hábiles. Ofrecer compensación adicional según el monto.',
    category: 'Cobros',
    indexed: true,
    updatedAt: new Date('2024-01-10')
  },
  {
    id: 'doc-2',
    title: 'Procedimiento para Retrasos en Pedidos',
    type: 'PROCEDURE',
    content: 'Para retrasos mayores a 30 minutos: 1) Contactar repartidor, 2) Informar tiempo estimado al cliente, 3) Ofrecer descuento del 20% si supera 60 minutos.',
    category: 'Entregas',
    indexed: true,
    updatedAt: new Date('2024-02-15')
  },
  {
    id: 'doc-3',
    title: 'FAQ - Cargos en Tarjeta',
    type: 'FAQ',
    content: '¿Por qué aparecen dos cargos? A veces el banco hace una autorización previa y luego el cargo real. Si ve dos cargos del mismo monto después de 24 horas, contacte soporte.',
    category: 'Pagos',
    indexed: true,
    updatedAt: new Date('2024-03-01')
  },
  {
    id: 'doc-4',
    title: 'Política de Alergias y Productos Incorrectos',
    type: 'POLICY',
    content: 'Los casos de alergias son PRIORIDAD CRÍTICA. Ofrecer reembolso completo + cupón de 15€. Reportar al restaurante inmediatamente.',
    category: 'Calidad',
    indexed: true,
    updatedAt: new Date('2024-01-20')
  },
  {
    id: 'doc-5',
    title: 'Manual de Atención al Cliente',
    type: 'MANUAL',
    content: 'Siempre responder con empatía. Usar el nombre del cliente. Ofrecer soluciones concretas. Tiempo de respuesta máximo: 2 horas.',
    category: 'General',
    indexed: true,
    updatedAt: new Date('2024-01-05')
  },
  {
    id: 'doc-6',
    title: 'FAQ - Modificaciones de Pedido',
    type: 'FAQ',
    content: '¿Puedo cambiar mi pedido después de enviarlo? Las modificaciones deben hacerse en los primeros 5 minutos. Después de ese tiempo, contacte soporte.',
    category: 'Pedidos',
    indexed: true,
    updatedAt: new Date('2024-02-28')
  }
];

// Helper functions
export const getUserById = (id: string): User | undefined => {
  return mockUsers.find(user => user.id === id);
};

export const getOrderById = (id: string): Order | undefined => {
  return mockOrders.find(order => order.id === id);
};

export const getClaimById = (id: string): Claim | undefined => {
  return mockClaims.find(claim => claim.id === id);
};

export const getOrdersByUserId = (userId: string): Order[] => {
  return mockOrders.filter(order => order.userId === userId);
};

export const getClaimsByUserId = (userId: string): Claim[] => {
  return mockClaims.filter(claim => claim.userId === userId);
};

export const getAnalysisForClaim = (claimId: string): ClaimAnalysis | undefined => {
  return mockClaimAnalyses.find(analysis => analysis.claimId === claimId);
};

export const getResponseForClaim = (claimId: string): ClaimResponse | undefined => {
  return mockClaimResponses.find(response => response.claimId === claimId);
};

export const getHistoryForClaim = (claimId: string): ClaimHistoryEvent[] => {
  return mockClaimHistory.filter(event => event.claimId === claimId);
};

export const getDocumentById = (id: string): KnowledgeDocument | undefined => {
  return mockKnowledgeDocuments.find(doc => doc.id === id);
};
