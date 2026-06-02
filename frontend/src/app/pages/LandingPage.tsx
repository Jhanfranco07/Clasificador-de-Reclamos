import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
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
import { formatCurrency } from '../lib/utils';

type Product = {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
};

type Restaurant = {
  id: string;
  name: string;
  category: string;
  rating: number;
  time: string;
  delivery: number;
  image: string;
  products: Product[];
};

type CartItem = Product & {
  restaurantName: string;
  quantity: number;
};

const restaurants: Restaurant[] = [
  {
    id: 'burger-palace',
    name: 'Burger Palace',
    category: 'Hamburguesas',
    rating: 4.8,
    time: '25-35 min',
    delivery: 4.9,
    image: 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=900',
    products: [
      { id: 'bp-1', name: 'Combo clasico', description: 'Hamburguesa, papas y gaseosa.', price: 24.5, image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600' },
      { id: 'bp-2', name: 'Doble cheese', description: 'Doble carne, cheddar y salsa especial.', price: 29.9, image: 'https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=600' },
      { id: 'bp-3', name: 'Crispy chicken burger', description: 'Pollo crocante, lechuga y mayo.', price: 27.5, image: 'https://images.unsplash.com/photo-1615297928064-24977384d0da?w=600' },
      { id: 'bp-4', name: 'Papas bacon cheddar', description: 'Papas fritas con bacon y queso.', price: 15.9, image: 'https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=600' },
    ],
  },
  {
    id: 'sushi-express',
    name: 'Sushi Express',
    category: 'Sushi',
    rating: 4.7,
    time: '35-45 min',
    delivery: 5.9,
    image: 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=900',
    products: [
      { id: 'se-1', name: 'Roll California', description: '8 piezas con palta y kanikama.', price: 32.9, image: 'https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=600' },
      { id: 'se-2', name: 'Combo makis', description: '24 piezas surtidas.', price: 45.8, image: 'https://images.unsplash.com/photo-1553621042-f6e147245754?w=600' },
      { id: 'se-3', name: 'Tempura roll', description: 'Roll crocante con salsa acevichada.', price: 36.5, image: 'https://images.unsplash.com/photo-1611143669185-af224c5e3252?w=600' },
      { id: 'se-4', name: 'Sashimi salmon', description: 'Cortes frescos de salmon.', price: 39.9, image: 'https://images.unsplash.com/photo-1625938145744-e38051539987?w=600' },
    ],
  },
  {
    id: 'pizza-napoli',
    name: 'Pizza Napoli',
    category: 'Pizzas',
    rating: 4.6,
    time: '30-40 min',
    delivery: 4.5,
    image: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=900',
    products: [
      { id: 'pn-1', name: 'Pizza margarita', description: 'Mozzarella, tomate y albahaca.', price: 28.0, image: 'https://images.unsplash.com/photo-1604068549290-dea0e4a305ca?w=600' },
      { id: 'pn-2', name: 'Pizza pepperoni', description: 'Pepperoni, mozzarella y oregano.', price: 34.0, image: 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600' },
      { id: 'pn-3', name: 'Pizza americana', description: 'Jamon, queso y salsa napolitana.', price: 31.5, image: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=600' },
      { id: 'pn-4', name: 'Lasagna bolognesa', description: 'Pasta al horno con salsa de carne.', price: 26.9, image: 'https://images.unsplash.com/photo-1619895092538-128341789043?w=600' },
    ],
  },
  {
    id: 'pollo-real',
    name: 'Pollo Real',
    category: 'Pollos',
    rating: 4.9,
    time: '20-30 min',
    delivery: 3.9,
    image: 'https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=900',
    products: [
      { id: 'pr-1', name: '1/4 pollo con papas', description: 'Clasico pollo a la brasa.', price: 21.9, image: 'https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600' },
      { id: 'pr-2', name: '1/2 pollo familiar', description: 'Papas, ensalada y cremas.', price: 42.5, image: 'https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=600' },
      { id: 'pr-3', name: 'Salchipapa brasa', description: 'Papas, hot dog y pollo trozado.', price: 18.5, image: 'https://images.unsplash.com/photo-1588756694278-4b8d1a4f3f3f?w=600' },
      { id: 'pr-4', name: 'Anticuchos mixtos', description: 'Brochetas con papas doradas.', price: 24.9, image: 'https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=600' },
    ],
  },
  {
    id: 'taco-loco',
    name: 'Taco Loco',
    category: 'Mexicana',
    rating: 4.5,
    time: '30-40 min',
    delivery: 5.5,
    image: 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=900',
    products: [
      { id: 'tl-1', name: 'Tacos al pastor', description: 'Tres tacos con pina y salsas.', price: 22.9, image: 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=600' },
      { id: 'tl-2', name: 'Burrito norteño', description: 'Carne, arroz, frijoles y queso.', price: 25.5, image: 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600' },
      { id: 'tl-3', name: 'Nachos supreme', description: 'Queso, guacamole y pico de gallo.', price: 19.9, image: 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=600' },
    ],
  },
  {
    id: 'dulce-mania',
    name: 'Dulce Mania',
    category: 'Postres',
    rating: 4.8,
    time: '20-30 min',
    delivery: 4.0,
    image: 'https://images.unsplash.com/photo-1551024601-bec78aea704b?w=900',
    products: [
      { id: 'dm-1', name: 'Cheesecake frutos rojos', description: 'Porcion individual cremosa.', price: 16.9, image: 'https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=600' },
      { id: 'dm-2', name: 'Brownie con helado', description: 'Brownie tibio y helado vainilla.', price: 18.5, image: 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=600' },
      { id: 'dm-3', name: 'Tres leches', description: 'Postre humedo con crema batida.', price: 14.9, image: 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600' },
    ],
  },
  {
    id: 'cafe-andino',
    name: 'Cafe Andino',
    category: 'Cafe',
    rating: 4.7,
    time: '15-25 min',
    delivery: 3.5,
    image: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=900',
    products: [
      { id: 'ca-1', name: 'Cafe latte', description: 'Cafe espresso con leche vaporizada.', price: 10.9, image: 'https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=600' },
      { id: 'ca-2', name: 'Sandwich mixto', description: 'Jamon, queso y pan artesanal.', price: 13.9, image: 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600' },
      { id: 'ca-3', name: 'Croissant mantequilla', description: 'Hojaldre fresco de la casa.', price: 8.9, image: 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600' },
    ],
  },
  {
    id: 'fresh-market',
    name: 'Fresh Market',
    category: 'Saludable',
    rating: 4.6,
    time: '25-35 min',
    delivery: 4.9,
    image: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=900',
    products: [
      { id: 'fm-1', name: 'Bowl quinoa', description: 'Quinoa, palta, pollo y vegetales.', price: 27.9, image: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600' },
      { id: 'fm-2', name: 'Wrap de pollo', description: 'Tortilla integral con pollo grillado.', price: 22.5, image: 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600' },
      { id: 'fm-3', name: 'Jugo detox', description: 'Piña, hierbabuena, apio y limon.', price: 12.9, image: 'https://images.unsplash.com/photo-1622597467836-f3285f2131b8?w=600' },
      { id: 'fm-4', name: 'Ensalada cesar', description: 'Pollo, parmesano y croutones.', price: 24.9, image: 'https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=600' },
    ],
  },
];

const categories = ['Todos', ...Array.from(new Set(restaurants.map((restaurant) => restaurant.category)))];

export default function LandingPage() {
  const [selectedCategory, setSelectedCategory] = useState('Todos');
  const [cart, setCart] = useState<CartItem[]>([]);

  const visibleRestaurants = useMemo(() => {
    if (selectedCategory === 'Todos') return restaurants;
    return restaurants.filter((restaurant) => restaurant.category === selectedCategory);
  }, [selectedCategory]);

  const cartTotal = cart.reduce((total, item) => total + item.price * item.quantity, 0);
  const deliveryTotal = cart.length ? Math.max(...cart.map((item) => {
    const restaurant = restaurants.find((current) => current.name === item.restaurantName);
    return restaurant?.delivery || 0;
  })) : 0;
  const finalTotal = cartTotal + deliveryTotal;

  const addToCart = (restaurant: Restaurant, product: Product) => {
    setCart((items) => {
      const existing = items.find((item) => item.id === product.id);
      if (existing) {
        return items.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...items, { ...product, restaurantName: restaurant.name, quantity: 1 }];
    });
  };

  const updateQuantity = (id: string, delta: number) => {
    setCart((items) =>
      items
        .map((item) => ({ ...item, quantity: item.quantity + delta }))
        .filter((item) => item.quantity > 0)
    );
  };

  const removeItem = (id: string) => {
    setCart((items) => items.filter((item) => item.id !== id));
  };

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <header className="border-b bg-white sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="size-8 text-orange-500" />
            <span className="font-bold text-2xl">SmartClaim AI</span>
          </div>
          <div className="flex items-center gap-3">
            <a href="#carrito" className="hidden md:block">
              <Button variant="outline" className="gap-2">
                <ShoppingCart className="size-4" />
                Carrito ({cart.reduce((total, item) => total + item.quantity, 0)})
              </Button>
            </a>
            <Link to="/login">
              <Button variant="ghost">Iniciar sesión</Button>
            </Link>
            <Link to="/register">
              <Button>Registrarse</Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="bg-white">
          <div className="container mx-auto px-4 py-10 grid lg:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
            <div className="space-y-6">
              <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-100">
                Catálogo público de delivery
              </Badge>
              <div>
                <h1 className="text-4xl md:text-5xl font-bold tracking-normal mb-4">
                  Elige tus productos, arma tu carrito y paga al iniciar sesión
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl">
                  Puedes explorar restaurantes y armar tu pedido sin cuenta. Al confirmar el pago,
                  inicia sesión para guardar tu historial y recibir soporte si algo sale mal.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <a href="#catalogo">
                  <Button size="lg" className="gap-2">
                    <ShoppingCart className="size-5" />
                    Ver catálogo
                  </Button>
                </a>
                <a href="#carrito">
                  <Button size="lg" variant="outline">
                    Revisar carrito
                  </Button>
                </a>
              </div>
              <div className="grid grid-cols-3 gap-3 max-w-xl">
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">8</p>
                  <p className="text-sm text-gray-500">Restaurantes</p>
                </div>
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">30+</p>
                  <p className="text-sm text-gray-500">Productos</p>
                </div>
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">24/7</p>
                  <p className="text-sm text-gray-500">Soporte disponible</p>
                </div>
              </div>
            </div>

            <div className="relative min-h-[360px] overflow-hidden rounded-lg">
              <img
                src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200"
                alt="Mesa con comida de delivery"
                className="absolute inset-0 h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                <p className="text-sm uppercase tracking-wide text-orange-200">Combo destacado</p>
                <h2 className="text-3xl font-bold">Combo urbano SmartClaim</h2>
                <p className="mt-2 text-white/85">Hamburguesa, papas y bebida con seguimiento en tiempo real.</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-2xl font-bold">{formatCurrency(32.9)}</span>
                  <Button
                    variant="secondary"
                    onClick={() => addToCart(restaurants[0], restaurants[0].products[0])}
                  >
                    Agregar al carrito
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="catalogo" className="container mx-auto px-4 py-10">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
            <div>
              <h2 className="text-3xl font-bold">Restaurantes y productos</h2>
              <p className="text-gray-600 mt-2">
                Elige una categoría y agrega productos al carrito.
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
                <article key={restaurant.id} className="bg-white border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  <div className="aspect-[4/3] overflow-hidden">
                    <img src={restaurant.image} alt={restaurant.name} className="h-full w-full object-cover" />
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

                    <div className="space-y-3">
                      {restaurant.products.map((product) => (
                        <div key={product.id} className="grid grid-cols-[64px_1fr_auto] gap-3 items-center rounded-lg bg-gray-50 p-3">
                          <img src={product.image} alt={product.name} className="size-16 rounded-lg object-cover" />
                          <div>
                            <p className="font-semibold leading-tight">{product.name}</p>
                            <p className="text-xs text-gray-500 line-clamp-2">{product.description}</p>
                            <p className="text-sm font-bold mt-1">{formatCurrency(product.price)}</p>
                          </div>
                          <Button size="sm" onClick={() => addToCart(restaurant, product)}>
                            <Plus className="size-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <aside id="carrito" className="bg-white border rounded-lg shadow-sm p-5 lg:sticky lg:top-24">
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
                          <img src={item.image} alt={item.name} className="size-14 rounded-lg object-cover" />
                          <div className="flex-1">
                            <div className="flex justify-between gap-2">
                              <div>
                                <p className="font-semibold leading-tight">{item.name}</p>
                                <p className="text-xs text-gray-500">{item.restaurantName}</p>
                              </div>
                              <button onClick={() => removeItem(item.id)} className="text-gray-400 hover:text-red-600">
                                <Trash2 className="size-4" />
                              </button>
                            </div>
                            <div className="flex items-center justify-between mt-3">
                              <div className="flex items-center gap-2">
                                <Button size="sm" variant="outline" onClick={() => updateQuantity(item.id, -1)}>
                                  <Minus className="size-3" />
                                </Button>
                                <span className="w-6 text-center font-semibold">{item.quantity}</span>
                                <Button size="sm" variant="outline" onClick={() => updateQuantity(item.id, 1)}>
                                  <Plus className="size-3" />
                                </Button>
                              </div>
                              <p className="font-bold">{formatCurrency(item.price * item.quantity)}</p>
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
                      <span>{formatCurrency(deliveryTotal)}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold pt-2">
                      <span>Total</span>
                      <span>{formatCurrency(finalTotal)}</span>
                    </div>
                  </div>

                  <Link to="/login">
                    <Button className="w-full" size="lg">
                      Iniciar sesión y pagar
                    </Button>
                  </Link>
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
            <div className="bg-white p-5 rounded-lg border">
              <MapPin className="size-6 text-orange-600 mb-3" />
              <h3 className="font-bold text-lg">Seguimiento del pedido</h3>
              <p className="text-gray-600 text-sm mt-2">Consulta estado, direccion y detalle del consumo.</p>
            </div>
            <div className="bg-white p-5 rounded-lg border">
              <HeadphonesIcon className="size-6 text-blue-600 mb-3" />
              <h3 className="font-bold text-lg">Atención inteligente</h3>
              <p className="text-gray-600 text-sm mt-2">Tus reclamos se ordenan por tipo, prioridad y estado de atención.</p>
            </div>
            <div className="bg-white p-5 rounded-lg border">
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
