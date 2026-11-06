import { Fragment } from 'react';
import { Link, useNavigate } from 'react-router';
import { Minus, Plus, ShoppingCart, Trash2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { useAuth } from '../../contexts/AuthContext';
import { formatCurrency } from '../../lib/utils';
import { useOrderQuote } from '../../lib/useOrderQuote';
import { useCart } from '../../lib/useCart';
import CartNotice from '../../components/CartNotice';
import ClientLayout from '../../components/ClientLayout';

export default function CartPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const cart = useCart();
  const { items } = cart;
  const { quote, error } = useOrderQuote(items);
  const Layout = isAuthenticated ? ClientLayout : Fragment;
  const change = (id: string, delta: number) => cart.update(items.map((item) => item.id === id ? { ...item, quantity: item.quantity + delta } : item).filter((item) => item.quantity > 0));

  return <Layout><div className="container mx-auto max-w-4xl px-4 py-8">
    <div className="mb-6 flex items-center justify-between gap-3"><div><h1 className="text-3xl font-bold">Tu carrito</h1><p className="text-gray-500">Revisa los productos antes de confirmar el pedido.</p></div><ShoppingCart className="size-7 shrink-0 text-orange-500" /></div>
    <Button asChild variant="ghost" className="mb-4"><Link to={isAuthenticated ? '/restaurants' : '/'}>Volver al catálogo</Link></Button>
    <CartNotice warning={cart.warning} reset={cart.reset} />
    {cart.blocked ? null : items.length === 0 ? (
      <div className="rounded-lg border border-dashed p-8 text-center"><p className="mb-4 text-gray-500">Tu carrito está vacío.</p><Button asChild><Link to={isAuthenticated ? '/restaurants' : '/'}>Explorar restaurantes</Link></Button></div>
    ) : <div className="space-y-4">
      {items.map((item) => <article key={item.id} className="flex gap-3 rounded-lg border border-border bg-card p-4 text-card-foreground shadow-sm">
        <ImageWithFallback src={item.image} alt={item.name} className="size-14 sm:size-20 shrink-0 rounded-md object-cover" />
        <div className="flex-1 min-w-0"><div className="flex justify-between gap-2"><div className="min-w-0 break-words"><h2 className="font-semibold">{item.name}</h2><p className="text-sm text-muted-foreground">{item.restaurantName}</p></div>
          <Button variant="ghost" size="icon" aria-label={`Eliminar ${item.name}`} onClick={() => cart.update(items.filter((current) => current.id !== item.id))}><Trash2 className="size-4" /></Button></div>
          <div className="mt-3 flex flex-wrap gap-3 items-center justify-between"><div className="flex items-center gap-2">
            <Button variant="outline" size="icon" aria-label={`Reducir cantidad de ${item.name}`} onClick={() => change(item.id, -1)}><Minus className="size-4" /></Button><span>{item.quantity}</span>
            <Button variant="outline" size="icon" aria-label={`Aumentar cantidad de ${item.name}`} onClick={() => change(item.id, 1)}><Plus className="size-4" /></Button></div>
            <strong>{quote ? formatCurrency((quote.items.find((line) => line.productId === Number(item.id))?.price ?? 0) * item.quantity) : 'Cotizando...'}</strong></div>
        </div>
      </article>)}
      <div className="flex flex-wrap gap-3 justify-between border-t pt-5 text-xl font-bold"><span>Total cotizado con cargos</span><span>{quote?.total != null ? formatCurrency(quote.total) : 'Pendiente'}</span></div>
      {(error || quote?.limitation) && <p role="alert" className="text-sm text-red-700">{error || quote?.limitation}</p>}
      {quote && !quote.canConfirm && [...new Set(quote.items.map(line => line.restaurantId))].map(restaurantId => {
        const name = quote.items.find(line => line.restaurantId === restaurantId)?.restaurantName;
        return <Button key={restaurantId} variant="outline" className="w-full h-auto whitespace-normal" onClick={() => {
          if (window.confirm(`Comprar los artículos de ${name} en un pedido separado. Los demás artículos permanecerán en el carrito. ¿Continuar?`)) {
            const destination = `/checkout?restaurant=${restaurantId}`;
            navigate(isAuthenticated ? destination : '/login', isAuthenticated ? undefined : { state: { from: destination } });
          }
        }}>Comprar por separado · {name}</Button>;
      })}
      <Button disabled={!quote?.canConfirm} className="w-full" size="lg" onClick={() => navigate(isAuthenticated ? '/checkout' : '/login', isAuthenticated ? undefined : { state: { from: '/checkout' } })}>{isAuthenticated ? 'Continuar al pago' : 'Iniciar sesión y pagar'}</Button>
    </div>}
  </div></Layout>;
}
