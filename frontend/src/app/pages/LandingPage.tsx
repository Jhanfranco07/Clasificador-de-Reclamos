import { Link } from 'react-router';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Package, Clock, HeadphonesIcon, Shield, Star, Bike, MapPin, ShoppingCart } from 'lucide-react';
import { formatCurrency } from '../lib/utils';

const restaurants = [
  {
    name: 'Burger Palace',
    category: 'Hamburguesas',
    rating: 4.8,
    time: '25-35 min',
    image: 'https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=800',
    products: [
      { name: 'Combo clasico', price: 24.5 },
      { name: 'Doble cheese', price: 29.9 },
    ],
  },
  {
    name: 'Sushi Express',
    category: 'Sushi',
    rating: 4.7,
    time: '35-45 min',
    image: 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=800',
    products: [
      { name: 'Roll California', price: 32.9 },
      { name: 'Combo makis', price: 45.8 },
    ],
  },
  {
    name: 'Pizza Napoli',
    category: 'Pizzas',
    rating: 4.6,
    time: '30-40 min',
    image: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800',
    products: [
      { name: 'Pizza Margarita', price: 28.0 },
      { name: 'Pizza pepperoni', price: 34.0 },
    ],
  },
];

const categories = ['Hamburguesas', 'Sushi', 'Pizzas', 'Pollos', 'Postres', 'Bebidas'];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <header className="border-b bg-white sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="size-8 text-orange-500" />
            <span className="font-bold text-2xl">SmartClaim AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost">Iniciar sesion</Button>
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
                Delivery demo con atencion inteligente
              </Badge>
              <div>
                <h1 className="text-4xl md:text-5xl font-bold tracking-normal mb-4">
                  Pide comida, sigue tu pedido y reporta problemas en un solo lugar
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl">
                  Explora restaurantes sin iniciar sesion. Cuando quieras comprar o registrar un reclamo,
                  SmartClaim AI te pedira acceso y activara el flujo de soporte con IA.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <a href="#catalogo">
                  <Button size="lg" className="gap-2">
                    <ShoppingCart className="size-5" />
                    Ver productos
                  </Button>
                </a>
                <Link to="/login">
                  <Button size="lg" variant="outline">
                    Iniciar sesion para comprar
                  </Button>
                </Link>
              </div>
              <div className="grid grid-cols-3 gap-3 max-w-xl">
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">30 min</p>
                  <p className="text-sm text-gray-500">Entrega promedio</p>
                </div>
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">4.8</p>
                  <p className="text-sm text-gray-500">Rating demo</p>
                </div>
                <div className="rounded-lg border bg-white p-3">
                  <p className="text-2xl font-bold">IA</p>
                  <p className="text-sm text-gray-500">Soporte asistido</p>
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
                <p className="text-sm uppercase tracking-wide text-orange-200">Pedido destacado</p>
                <h2 className="text-3xl font-bold">Combo urbano SmartClaim</h2>
                <p className="mt-2 text-white/85">Hamburguesa, papas y bebida con seguimiento en tiempo real.</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-2xl font-bold">{formatCurrency(32.9)}</span>
                  <Link to="/login">
                    <Button variant="secondary">Comprar ahora</Button>
                  </Link>
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
                Catalogo publico de demostracion. La compra requiere iniciar sesion.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <Badge key={category} variant="outline" className="bg-white">
                  {category}
                </Badge>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {restaurants.map((restaurant) => (
              <article key={restaurant.name} className="bg-white border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
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
                      Delivery
                    </span>
                  </div>

                  <div className="space-y-3">
                    {restaurant.products.map((product) => (
                      <div key={product.name} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                        <div>
                          <p className="font-semibold">{product.name}</p>
                          <p className="text-sm text-gray-500">{formatCurrency(product.price)}</p>
                        </div>
                        <Link to="/login">
                          <Button size="sm">Agregar</Button>
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              </article>
            ))}
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
              <h3 className="font-bold text-lg">Reclamos con IA</h3>
              <p className="text-gray-600 text-sm mt-2">Clasificacion, prioridad, RAG y respuesta sugerida para revision.</p>
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
