import { Link } from 'react-router';
import { Button } from '../components/ui/button';
import { Package, Clock, HeadphonesIcon, Shield, Zap, TrendingUp } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-blue-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="size-8 text-orange-500" />
            <span className="font-bold text-2xl">SmartClaim AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/login">
              <Button variant="ghost">Iniciar sesión</Button>
            </Link>
            <Link to="/register">
              <Button>Registrarse</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-orange-600 to-blue-600 bg-clip-text text-transparent">
            Tu delivery inteligente con atención revolucionaria
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Pedidos rápidos, seguimiento en tiempo real y un sistema de atención al cliente
            impulsado por IA que resuelve tus problemas en minutos.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/login">
              <Button size="lg" className="text-lg px-8">
                Realizar pedido
              </Button>
            </Link>
            <Link to="/help">
              <Button size="lg" variant="outline" className="text-lg px-8">
                Centro de ayuda
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">¿Por qué elegir SmartClaim AI?</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
              <Zap className="size-6 text-orange-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Pedidos ultrarrápidos</h3>
            <p className="text-gray-600">
              Entrega en 30 minutos o menos. Seguimiento en tiempo real de tu pedido.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <HeadphonesIcon className="size-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Atención inteligente 24/7</h3>
            <p className="text-gray-600">
              Sistema de IA que clasifica y resuelve tus reclamos automáticamente.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <Shield className="size-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Pagos seguros</h3>
            <p className="text-gray-600">
              Múltiples métodos de pago protegidos con la mejor tecnología.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <Clock className="size-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Respuesta en minutos</h3>
            <p className="text-gray-600">
              ¿Problema con tu pedido? Nuestro sistema responde en menos de 5 minutos.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-pink-100 rounded-lg flex items-center justify-center mb-4">
              <TrendingUp className="size-6 text-pink-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Mejora continua</h3>
            <p className="text-gray-600">
              Sistema que aprende de cada interacción para mejorar tu experiencia.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="size-12 bg-amber-100 rounded-lg flex items-center justify-center mb-4">
              <Package className="size-6 text-amber-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Miles de restaurantes</h3>
            <p className="text-gray-600">
              Tu comida favorita de los mejores restaurantes a un click de distancia.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-orange-500 to-blue-500 py-16">
        <div className="container mx-auto px-4 text-center text-white">
          <h2 className="text-4xl font-bold mb-4">¿Listo para empezar?</h2>
          <p className="text-xl mb-8 opacity-90">
            Únete a miles de usuarios que confían en SmartClaim AI
          </p>
          <Link to="/register">
            <Button size="lg" variant="secondary" className="text-lg px-12">
              Crear cuenta gratis
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Package className="size-6 text-orange-500" />
                <span className="font-bold text-white">SmartClaim AI</span>
              </div>
              <p className="text-sm">
                La plataforma de delivery más inteligente del mercado.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Producto</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Cómo funciona</a></li>
                <li><a href="#" className="hover:text-white">Precios</a></li>
                <li><a href="#" className="hover:text-white">Restaurantes</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Soporte</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/help" className="hover:text-white">Centro de ayuda</Link></li>
                <li><a href="#" className="hover:text-white">Contacto</a></li>
                <li><a href="#" className="hover:text-white">Políticas</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Términos</a></li>
                <li><a href="#" className="hover:text-white">Privacidad</a></li>
                <li><a href="#" className="hover:text-white">Cookies</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm">
            <p>© 2024 SmartClaim AI. Proyecto académico - Universidad.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
