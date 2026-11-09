import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN'
  }).format(amount);
}

const timeZone = 'America/Lima';

function toDate(date: Date | string): Date {
  if (date instanceof Date) return date;
  // Calendar-only values keep their day. SQL timestamps without an offset are UTC.
  if (/^\d{4}-\d{2}-\d{2}$/.test(date)) return new Date(date + 'T12:00:00Z');
  if (/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(date)) {
    return new Date(date.replace(' ', 'T') + 'Z');
  }
  return new Date(date);
}

export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat('es-PE', {
    timeZone,
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(toDate(date));
}

export function formatDateTime(date: Date | string): string {
  return new Intl.DateTimeFormat('es-PE', {
    timeZone,
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(toDate(date));
}

export function formatTime(date: Date | string): string {
  return new Intl.DateTimeFormat('es-PE', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit'
  }).format(toDate(date));
}

export function getRelativeTime(date: Date | string): string {
  const now = new Date();
  const parsed = toDate(date);
  const diffMs = now.getTime() - parsed.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins} min`;
  if (diffHours < 24) return `Hace ${diffHours}h`;
  if (diffDays < 7) return `Hace ${diffDays}d`;
  return formatDate(parsed);
}
