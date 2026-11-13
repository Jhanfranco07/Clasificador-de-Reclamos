import { useState } from 'react';
import { CART_KEY, CartItem, readCart, parseCart } from './cart';

export function useCart() {
  const [snapshot, setSnapshot] = useState(readCart);
  const persist = (items: CartItem[]) => {
    const next = parseCart(JSON.stringify(items));
    if (next.blocked) { setSnapshot({ ...snapshot, warning: 'No se pudo agregar el artículo: sus datos o cantidad no son válidos.' }); return false; }
    try {
      window.localStorage.setItem(CART_KEY, JSON.stringify(next.items));
      setSnapshot(next);
      return true;
    } catch {
      setSnapshot({ ...snapshot, blocked: true, warning: 'No se pudo guardar el carrito. Revisa el almacenamiento antes de continuar.' });
      return false;
    }
  };
  return { ...snapshot, update: (next: CartItem[] | ((items: CartItem[]) => CartItem[])) => {
    if (snapshot.blocked) return false;
    return persist(typeof next === 'function' ? next(snapshot.items) : next);
  }, reset: () => persist([]) };
}
