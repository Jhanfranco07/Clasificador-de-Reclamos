import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Minus, Plus, ShoppingCart, Trash2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { useAuth } from '../../contexts/AuthContext';
import { formatCurrency } from '../../lib/utils';
import { CART_KEY, CartItem } from './CatalogPage';

export default function CartPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<CartItem[]>(() => JSON.parse(window.localStorage.getItem(CART_KEY) || '[]'));
  const total = useMemo(() => items.reduce((sum, item) => sum + item.price * item.quantity, 0), [items]);
  const save = (next: CartItem[]) => { setItems(next); window.localStorage.setItem(CART_KEY, JSON.stringify(next)); };
  const change = (id: string, delta: number) => save(items.map((item) => item.id === id ? { ...item, quantity: item.quantity + delta } : item).filter((item) => item.quantity > 0));

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between"><div><h1 className="text-3xl font-bold">Tu carrito</h1><p className="text-gray-500">Revisa los productos antes de confirmar el pedido.</p></div><ShoppingCart className="size-7 text-orange-500" /></div>
      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center"><p className="mb-4 text-gray-500">Tu carrito está vacío.</p><Button asChild><Link to="/restaurants">Explorar restaurantes</Link></Button></div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => <article key={item.id} className="flex gap-4 rounded-lg border bg-white p-4 dark:bg-gray-900"><ImageWithFallback src={item.image} alt={item.name} className="size-20 rounded-md object-cover" /><div className="flex-1"><div className="flex justify-between gap-3"><div><h2 className="font-semibold">{item.name}</h2><p className="text-sm text-gray-500">{item.restaurantName}</p></div><Button variant="ghost" size="icon" onClick={() => save(items.filter((current) => current.id !== item.id))}><Trash2 className="size-4" /></Button></div><div className="mt-3 flex items-center justify-between"><div className="flex items-center gap-2"><Button variant="outline" size="icon" onClick={() => change(item.id, -1)}><Minus className="size-4" /></Button><span>{item.quantity}</span><Button variant="outline" size="icon" onClick={() => change(item.id, 1)}><Plus className="size-4" /></Button></div><strong>{formatCurrency(item.price * item.quantity)}</strong></div></div></article>)}
          <div className="flex items-center justify-between border-t pt-5 text-xl font-bold"><span>Total</span><span>{formatCurrency(total)}</span></div>
          <Button className="w-full" size="lg" onClick={() => navigate(isAuthenticated ? '/checkout' : '/login', isAuthenticated ? undefined : { state: { from: '/checkout' } })}>{isAuthenticated ? 'Continuar al pago' : 'Iniciar sesión y pagar'}</Button>
        </div>
      )}
    </div>
  );
}
