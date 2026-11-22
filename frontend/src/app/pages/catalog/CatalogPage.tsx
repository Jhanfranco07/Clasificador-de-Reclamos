import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Bike,
  Clock,
  HeadphonesIcon,
  MapPin,
  Minus,
  Package,
  Plus,
  Shield,
  ShoppingCart,
  Star,
  Trash2,
} from 'lucide-react';
import { formatCurrency } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { getCatalog } from '../../lib/api';
import { useOrderQuote } from '../../lib/useOrderQuote';
import { useCart } from '../../lib/useCart';
import CartNotice from '../../components/CartNotice';
export { CART_KEY } from '../../lib/cart';
export type { CartItem } from '../../lib/cart';

export type Product = {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
};

export type Restaurant = {
  id: string;
  name: string;
  category: string;
  rating: number;
  time: string;
  delivery: number;
  image: string;
  products: Product[];
};

export default function CatalogPage({ internal = false }: { internal?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, currentUser, logout } = useAuth();
  const [apiRestaurants, setApiRestaurants] = useState<Restaurant[]>([]);
  const [catalogError, setCatalogError] = useState('');
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('Todos');
  const cartState = useCart();
  const { items: cart, update: setCart } = cartState;

  useEffect(() => {
    getCatalog()
      .then((result) => {
        setApiRestaurants(result.items as Restaurant[]);
      })
      .catch(() => {
        setApiRestaurants([]);
        setCatalogError('No se pudo cargar el catálogo. No se muestran comercios de respaldo.');
      }).finally(() => setCatalogLoading(false));
  }, []);

  const restaurants = apiRestaurants;
  const featuredRestaurant = restaurants.find((restaurant) => restaurant.products.length > 0);
  const featuredProduct = featuredRestaurant?.products[0];
  const categories = useMemo(
    () => ['Todos', ...Array.from(new Set(restaurants.map((restaurant) => restaurant.category)))],
    [restaurants]
  );
  const totalProducts = useMemo(
    () => restaurants.reduce((total, restaurant) => total + restaurant.products.length, 0),
    [restaurants]
  );

  const visibleRestaurants = useMemo(() => {
    if (selectedCategory === 'Todos') return restaurants;
    return restaurants.filter((restaurant) => restaurant.category === selectedCategory);
  }, [selectedCategory, restaurants]);

  const { quote, error: quoteError } = useOrderQuote(cart);
  const cartTotal = quote?.subtotal ?? 0;
  const deliveryTotal = quote?.delivery;
  const finalTotal = quote?.total;

  const addToCart = (restaurant: Restaurant, product: Product) => {
    setCart((items) => {
      const existing = items.find((item) => item.id === product.id);
      if (existing) {
        return items.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...items, { ...product, restaurantName: restaurant.name, restaurantImage: restaurant.image, quantity: 1 }];
    });
  };

  const updateQuantity = (id: string, delta: number) => {
    setCart((items) =>
      items
        .map((item) => (item.id === id ? { ...item, quantity: item.quantity + delta } : item))
        .filter((item) => item.quantity > 0)
    );
  };

  const removeItem = (id: string) => {
    setCart((items) => items.filter((item) => item.id !== id));
  };

  const handleCheckout = () => {
    if (!cart.length) return;
    navigate(isAuthenticated ? '/checkout' : '/login', isAuthenticated ? undefined : { state: { from: '/checkout' } });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {!internal && <header className="border-b border-border bg-card/95 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex flex-col gap-3 sm:flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex size-10 items-center justify-center rounded-xl bg-orange-500 text-white shadow-sm">
              <Package className="size-6" />
            </span>
            <span className="font-bold text-2xl">SmartClaim AI</span>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <a href="#carrito" className="hidden md:block">
              <Button variant="outline" className="gap-2">
                <ShoppingCart className="size-4" />
                Carrito ({cart.reduce((total, item) => total + item.quantity, 0)})
              </Button>
            </a>
            {isAuthenticated ? (
              <>
                <div className="hidden lg:flex items-center gap-1">
                  <Link to="/orders"><Button variant="ghost">Mis pedidos</Button></Link>
                  <Link to="/claims"><Button variant="ghost">Mis reclamos</Button></Link>
                  <Link to="/help"><Button variant="ghost">Ayuda</Button></Link>
                </div>
                <Link to="/dashboard">
                  <Button variant="ghost">Hola, {currentUser?.name?.split(' ')[0]}</Button>
                </Link>
                <Button variant="outline" onClick={() => logout()}>Cerrar sesión</Button>
              </>
            ) : (
              <>
                <Link to="/login" state={{ from: `${location.pathname}${location.search}` }}>
                  <Button variant="ghost">Iniciar sesión</Button>
                </Link>
                <Link to="/register" state={{ from: `${location.pathname}${location.search}` }}>
                  <Button>Registrarse</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>}

      <main>
        <div className="container mx-auto px-4"><CartNotice warning={cartState.warning} reset={cartState.reset} /></div>
        <section className="bg-card">
          <div className="container mx-auto px-4 py-10 grid lg:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
            <div className="space-y-6 min-w-0">
              <Badge className="max-w-full whitespace-normal bg-orange-100 text-orange-700 hover:bg-orange-100">
                Proyecto académico · pedidos y pagos de demostración
              </Badge>
              <div>
                <h1 className="text-4xl md:text-5xl font-bold tracking-normal mb-4">
                  Comida peruana, chifa, sushi y más en un solo lugar
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl">
                  Explora restaurantes, agrega tus favoritos al carrito y confirma tu pedido
                  cuando estés listo. Si algo sale mal, soporte puede revisar tu caso desde tu historial.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <a href="#catalogo">
                  <Button size="lg" className="gap-2">
                    <ShoppingCart className="size-5" />
                    Ver restaurantes
                  </Button>
                </a>
                <a href="#carrito">
                  <Button size="lg" variant="outline">
                    Ver carrito
                  </Button>
                </a>
              </div>
              <div className="grid grid-cols-3 gap-3 max-w-xl">
                <div className="min-w-0 break-words rounded-lg border bg-white p-2 sm:p-3 shadow-sm">
                  <p className="text-2xl font-bold">{restaurants.length}</p>
                  <p className="text-sm text-gray-500">Restaurantes</p>
                </div>
                <div className="min-w-0 break-words rounded-lg border bg-white p-2 sm:p-3 shadow-sm">
                  <p className="text-2xl font-bold">{totalProducts}</p>
                  <p className="text-sm text-gray-500">Productos</p>
                </div>
                <div className="min-w-0 break-words rounded-lg border bg-white p-2 sm:p-3 shadow-sm">
                  <p className="text-2xl font-bold">En la app</p>
                  <p className="text-sm text-gray-500">Seguimiento del reclamo</p>
                </div>
              </div>
            </div>

            <div className="relative min-h-[360px] overflow-hidden rounded-lg shadow-2xl shadow-slate-200">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200"
                alt="Mesa con comida de delivery"
                className="absolute inset-0 h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                <p className="text-sm uppercase tracking-wide text-orange-200">Selección del catálogo de demostración</p>
                <h2 className="text-3xl font-bold">{featuredProduct?.name || 'Sin producto destacado'}</h2>
                <p className="mt-2 text-white/85">Precio de catálogo; no representa una promoción o descuento.</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-2xl font-bold">{featuredProduct ? formatCurrency(featuredProduct.price) : 'No disponible'}</span>
                  <Button
                    variant="secondary"
                    disabled={!featuredProduct || cartState.blocked}
                    onClick={() => { if (featuredRestaurant && featuredProduct) addToCart(featuredRestaurant, featuredProduct); }}
                  >
                    Agregar al carrito
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="catalogo" className="container mx-auto px-4 py-10">
          {catalogLoading && <p role="status">Cargando catálogo...</p>}
          {catalogError && <p role="alert">{catalogError}</p>}
          {!catalogLoading && !catalogError && restaurants.length === 0 && <p>No hay restaurantes disponibles.</p>}
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
            <div>
              <h2 className="text-3xl font-bold">Restaurantes disponibles</h2>
              <p className="text-gray-600 mt-2">
                Filtra por categoría, revisa precios en soles y arma tu pedido.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <button key={category} onClick={() => setSelectedCategory(category)}>
                  <Badge
                    variant={selectedCategory === category ? 'default' : 'outline'}
                    className={selectedCategory === category ? '' : 'bg-white'}
                  >
                    {category}
                  </Badge>
                </button>
              ))}
            </div>
          </div>

          <div className="grid lg:grid-cols-[1fr_360px] gap-6 items-start">
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
              {visibleRestaurants.map((restaurant) => (
                <article key={restaurant.id} className="bg-card text-card-foreground border border-border rounded-lg overflow-hidden shadow-sm hover:-translate-y-1 hover:shadow-xl dark:hover:shadow-slate-950/40 transition-all duration-200">
                  <div className="aspect-[4/3] overflow-hidden">
                    <ImageWithFallback src={restaurant.image} alt={restaurant.name} className="h-full w-full object-cover" />
                  </div>
                  <div className="p-5 space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-xl font-bold">{restaurant.name}</h3>
                        <p className="text-sm text-gray-500">{restaurant.category}</p>
                      </div>
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                        <Star className="size-3 mr-1 fill-current" />
                        {restaurant.rating}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Clock className="size-4" />
                        {restaurant.time}
                      </span>
                      <span className="flex items-center gap-1">
                        <Bike className="size-4" />
                        {formatCurrency(restaurant.delivery)}
                      </span>
                    </div>
                    <Button asChild variant="outline" className="w-full">
                      <Link to={`/restaurants/${restaurant.id}`}>Ver restaurante</Link>
                    </Button>

                    <div className="space-y-3">
                      {restaurant.products.map((product) => (
                        <div key={product.id} className="grid grid-cols-[64px_1fr_auto] gap-3 items-center rounded-lg bg-muted/60 p-3">
                          <ImageWithFallback src={product.image} alt={product.name} className="size-16 rounded-lg object-cover" />
                          <div>
                            <p className="font-semibold leading-tight">{product.name}</p>
                            <p className="text-xs text-gray-500 line-clamp-2">{product.description}</p>
                            <p className="text-sm font-bold mt-1">{formatCurrency(product.price)}</p>
                          </div>
                          <Button size="sm" disabled={cartState.blocked} aria-label={`Agregar ${product.name}`} onClick={() => addToCart(restaurant, product)}>
                            <Plus className="size-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <aside id="carrito" className="bg-card text-card-foreground border border-border rounded-lg shadow-sm dark:shadow-slate-950/25 p-5 lg:sticky lg:top-24">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold">Tu carrito</h2>
                  <p className="text-sm text-gray-500">Resumen del pedido</p>
                </div>
                <ShoppingCart className="size-6 text-orange-500" />
              </div>

              {cart.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-center text-gray-500">
                  Agrega productos para armar tu pedido.
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                    {cart.map((item) => (
                      <div key={item.id} className="rounded-lg border p-3">
                        <div className="flex gap-3">
                          <ImageWithFallback src={item.image} alt={item.name} className="size-14 rounded-lg object-cover" />
                          <div className="flex-1">
                            <div className="flex justify-between gap-2">
                              <div>
                                <p className="font-semibold leading-tight">{item.name}</p>
                                <p className="text-xs text-gray-500">{item.restaurantName}</p>
                              </div>
                              <button aria-label={`Eliminar ${item.name}`} onClick={() => removeItem(item.id)} className="text-gray-400 hover:text-red-600">
                                <Trash2 className="size-4" />
                              </button>
                            </div>
                            <div className="flex items-center justify-between mt-3">
                              <div className="flex items-center gap-2">
                                <Button size="sm" variant="outline" aria-label={`Reducir cantidad de ${item.name}`} onClick={() => updateQuantity(item.id, -1)}>
                                  <Minus className="size-3" />
                                </Button>
                                <span className="w-6 text-center font-semibold">{item.quantity}</span>
                                <Button size="sm" variant="outline" aria-label={`Aumentar cantidad de ${item.name}`} onClick={() => updateQuantity(item.id, 1)}>
                                  <Plus className="size-3" />
                                </Button>
                              </div>
                              <p className="font-bold">{quote ? formatCurrency((quote.items.find((line) => line.productId === Number(item.id))?.price ?? 0) * item.quantity) : 'Cotizando...'}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="border-t pt-4 space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Subtotal</span>
                      <span>{formatCurrency(cartTotal)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Delivery estimado</span>
                      <span>{deliveryTotal != null ? formatCurrency(deliveryTotal) : 'Pendiente'}</span>
                    </div>
                    <div className="flex justify-between"><span>Servicio</span><span>{quote?.service != null ? formatCurrency(quote.service) : 'Pendiente'}</span></div>
                    <div className="flex justify-between text-lg font-bold pt-2">
                      <span>Total</span>
                      <span>{finalTotal != null ? formatCurrency(finalTotal) : 'Pendiente'}</span>
                    </div>
                  </div>

                  {(quoteError || quote?.limitation) && <p role="alert" className="text-sm text-red-700">{quoteError || quote?.limitation}</p>}
                  <Button className="w-full" size="lg" onClick={handleCheckout} disabled={!quote?.canConfirm}>
                    {isAuthenticated ? 'Continuar al pago' : 'Iniciar sesión y pagar'}
                  </Button>
                  <p className="text-xs text-gray-500 text-center">
                    Al continuar, inicia sesión para confirmar el pedido y guardar tu historial.
                  </p>
                </div>
              )}
            </aside>
          </div>
        </section>

        <section className="container mx-auto px-4 py-10">
          <div className="grid md:grid-cols-3 gap-5">
            <div className="bg-card text-card-foreground p-5 rounded-lg border border-border">
              <MapPin className="size-6 text-orange-600 mb-3" />
              <h3 className="font-bold text-lg">Seguimiento del pedido</h3>
              <p className="text-gray-600 text-sm mt-2">Consulta estado, direccion y detalle del consumo.</p>
            </div>
            <div className="bg-card text-card-foreground p-5 rounded-lg border border-border">
              <HeadphonesIcon className="size-6 text-blue-600 mb-3" />
              <h3 className="font-bold text-lg">Atención inteligente</h3>
              <p className="text-gray-600 text-sm mt-2">Tus reclamos se ordenan por tipo, prioridad y estado de atención.</p>
            </div>
            <div className="bg-card text-card-foreground p-5 rounded-lg border border-border">
              <Shield className="size-6 text-green-600 mb-3" />
              <h3 className="font-bold text-lg">Gestion por agente</h3>
              <p className="text-gray-600 text-sm mt-2">El agente revisa, edita, aprueba, escala o cierra el reclamo.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}


