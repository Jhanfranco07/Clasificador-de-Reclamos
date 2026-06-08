import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { ArrowLeft, Clock, Plus, Star } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { formatCurrency } from '../../lib/utils';
import { getCatalog } from '../../lib/api';
import { CART_KEY, CartItem, fallbackRestaurants, Restaurant } from './CatalogPage';

export default function RestaurantPage() {
  const { id } = useParams();
  const [restaurant, setRestaurant] = useState<Restaurant | null>(
    fallbackRestaurants.find((item) => item.id === id) || null
  );

  useEffect(() => {
    getCatalog().then(({ items }) => {
      const found = items.find((item) => item.id === id) as Restaurant | undefined;
      if (found) setRestaurant(found);
    }).catch(() => undefined);
  }, [id]);

  const add = (product: Restaurant['products'][number]) => {
    if (!restaurant) return;
    const current = JSON.parse(window.localStorage.getItem(CART_KEY) || '[]') as CartItem[];
    const existing = current.find((item) => item.id === product.id);
    const next = existing
      ? current.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
      : [...current, { ...product, quantity: 1, restaurantName: restaurant.name, restaurantImage: restaurant.image }];
    window.localStorage.setItem(CART_KEY, JSON.stringify(next));
  };

  if (!restaurant) return <div className="p-8 text-center">Restaurante no encontrado.</div>;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8">
        <Button asChild variant="ghost" className="mb-5"><Link to="/restaurants"><ArrowLeft className="mr-2 size-4" />Volver al catálogo</Link></Button>
        <div className="overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-lg dark:shadow-slate-950/30">
          <ImageWithFallback src={restaurant.image} alt={restaurant.name} className="h-72 w-full object-cover" />
          <div className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div><h1 className="text-3xl font-bold">{restaurant.name}</h1><p className="mt-1 text-gray-500">{restaurant.category}</p></div>
              <div className="flex gap-4 text-sm"><span className="flex items-center gap-1"><Star className="size-4 text-amber-500" />{restaurant.rating}</span><span className="flex items-center gap-1"><Clock className="size-4" />{restaurant.time}</span></div>
            </div>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {restaurant.products.map((product) => (
                <article key={product.id} className="grid grid-cols-[96px_1fr_auto] items-center gap-4 rounded-lg border border-border bg-muted/40 p-3">
                  <ImageWithFallback src={product.image} alt={product.name} className="size-24 rounded-md object-cover" />
                  <div><h2 className="font-semibold">{product.name}</h2><p className="text-sm text-gray-500">{product.description}</p><p className="mt-2 font-bold">{formatCurrency(product.price)}</p></div>
                  <Button size="icon" onClick={() => add(product)} aria-label={`Agregar ${product.name}`}><Plus className="size-4" /></Button>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
