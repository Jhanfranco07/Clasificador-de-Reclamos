export const CART_KEY = 'smartclaim_pending_cart';
export type CartItem = {
  id: string; name: string; price: number; image: string; description?: string;
  restaurantName: string; restaurantImage?: string; quantity: number;
};
export type CartSnapshot = { items: CartItem[]; warning: string; blocked: boolean };
const empty = (): CartSnapshot => ({ items: [], warning: '', blocked: false });

export function parseCart(raw: string | null): CartSnapshot {
  if (raw === null) return empty();
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) throw new Error();
    const ids = new Set<string>();
    const items = value.map((item): CartItem => {
      if (!item || typeof item !== 'object' || typeof item.id !== 'string'
          || !/^\d+$/.test(item.id) || !Number.isSafeInteger(Number(item.id)) || Number(item.id) <= 0
          || typeof item.name !== 'string' || !item.name.trim()
          || typeof item.restaurantName !== 'string' || !item.restaurantName.trim()
          || typeof item.price !== 'number' || !Number.isFinite(item.price) || item.price < 0
          || !Number.isInteger(item.quantity) || item.quantity <= 0 || item.quantity > 2147483647
          || (item.image != null && typeof item.image !== 'string')
          || (item.restaurantImage != null && typeof item.restaurantImage !== 'string')) throw new Error();
      const id = String(Number(item.id));
      if (ids.has(id)) throw new Error();
      ids.add(id);
      return { id, name: item.name.trim(), restaurantName: item.restaurantName.trim(),
        price: item.price, quantity: item.quantity, image: item.image || '', restaurantImage: item.restaurantImage };
    });
    return { ...empty(), items };
  } catch {
    return { items: [], blocked: true, warning: 'El carrito contiene datos inválidos. Se conservaron sin cambios. Restablécelo para volver a comprar.' };
  }
}

export function readCart(): CartSnapshot {
  try { return parseCart(window.localStorage.getItem(CART_KEY)); }
  catch { return { items: [], blocked: true, warning: 'No se pudo acceder al almacenamiento del carrito. Habilita el almacenamiento y vuelve a intentarlo.' }; }
}
