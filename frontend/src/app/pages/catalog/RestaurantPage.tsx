import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { ArrowLeft, Clock, Plus, Star } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { formatCurrency } from '../../lib/utils';
import { getCatalog } from '../../lib/api';
import type { Restaurant } from './CatalogPage';
import { useCart } from '../../lib/useCart';
import CartNotice from '../../components/CartNotice';
import ClientLayout from '../../components/ClientLayout';
import { useAuth } from '../../contexts/AuthContext';
import { Fragment } from 'react';

export default function RestaurantPage() {
  const { id } = useParams();
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const cart = useCart();
  const [notice, setNotice] = useState('');
  const { isAuthenticated } = useAuth();
  const Layout = isAuthenticated ? ClientLayout : Fragment;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    getCatalog().then(({ items }) => {
      if (!active) return;
      const found = items.find((item) => item.id === id) as Restaurant | undefined;
      setRestaurant(found || null);
    }).catch(() => { if (active) setError('No se pudo cargar el restaurante.'); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  const add = (product: Restaurant['products'][number]) => {
    if (!restaurant) return;
    const current = cart.items;
    const existing = current.find((item) => item.id === product.id);
    const next = existing
      ? current.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
      : [...current, { ...product, quantity: 1, restaurantName: restaurant.name, restaurantImage: restaurant.image }];
    if (cart.update(next)) setNotice(`${product.name} agregado al carrito.`);
  };

  if (loading || error || !restaurant) return <Layout><div className="p-8"><Button asChild variant="outline"><Link to={isAuthenticated ? '/restaurants' : '/'}>Volver al catálogo</Link></Button>
    {loading ? <p role="status">Cargando restaurante...</p> : error ? <p role="alert">{error}</p> : <p>Restaurante no encontrado.</p>}</div></Layout>;

  return (
    <Layout><div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-wrap justify-between gap-3 mb-5"><Button asChild variant="ghost"><Link to={isAuthenticated ? '/restaurants' : '/'}><ArrowLeft className="mr-2 size-4" />Volver al catálogo</Link></Button><Button asChild variant="outline"><Link to="/cart">Ver carrito ({cart.items.reduce((sum, item) => sum + item.quantity, 0)})</Link></Button></div>
        <CartNotice warning={cart.warning} reset={cart.reset} />
        {notice && <p role="status">{notice}</p>}
        <div className="overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-lg dark:shadow-slate-950/30">
          <ImageWithFallback src={restaurant.image} alt={restaurant.name} className="h-72 w-full object-cover" />
          <div className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div><h1 className="text-3xl font-bold">{restaurant.name}</h1><p className="mt-1 text-gray-500">{restaurant.category}</p></div>
              <div className="flex gap-4 text-sm"><span className="flex items-center gap-1"><Star className="size-4 text-amber-500" />{restaurant.rating}</span><span className="flex items-center gap-1"><Clock className="size-4" />{restaurant.time}</span></div>
            </div>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {restaurant.products.map((product) => (
                <article key={product.id} className="grid grid-cols-[56px_minmax(0,1fr)_auto] sm:grid-cols-[96px_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-border bg-muted/40 p-3">
                  <ImageWithFallback src={product.image} alt={product.name} className="size-14 sm:size-24 rounded-md object-cover" />
                  <div className="min-w-0 break-words"><h2 className="font-semibold">{product.name}</h2><p className="text-sm text-gray-500">{product.description}</p><p className="mt-2 font-bold">{formatCurrency(product.price)}</p></div>
                  <Button size="icon" disabled={cart.blocked} onClick={() => add(product)} aria-label={`Agregar ${product.name}`}><Plus className="size-4" /></Button>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div></Layout>
  );
}
