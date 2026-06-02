import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../../components/ui/accordion';
import { Search, MessageCircle, Mail, Phone, HelpCircle, CreditCard, Package, Shield } from 'lucide-react';
import ClientLayout from '../../components/ClientLayout';

export default function HelpCenterPage() {
  const faqCategories = [
    {
      title: 'Pedidos',
      icon: Package,
      faqs: [
        {
          q: '¿Cómo puedo rastrear mi pedido?',
          a: 'Puedes rastrear tu pedido en tiempo real desde la sección "Mis pedidos". Allí verás el estado actual, la ubicación del repartidor y el tiempo estimado de entrega.'
        },
        {
          q: '¿Puedo modificar mi pedido después de haberlo realizado?',
          a: 'Las modificaciones solo están disponibles en los primeros 5 minutos después de realizar el pedido. Pasado ese tiempo, contacta con soporte para casos especiales.'
        },
        {
          q: '¿Qué hago si mi pedido no llegó?',
          a: 'Si tu pedido no ha llegado en el tiempo estimado, primero verifica el estado en la app. Si ya pasó más de 30 minutos del tiempo estimado, crea un reclamo y te ayudaremos inmediatamente.'
        }
      ]
    },
    {
      title: 'Pagos',
      icon: CreditCard,
      faqs: [
        {
          q: '¿Qué métodos de pago aceptan?',
          a: 'Aceptamos tarjetas de crédito/débito (Visa, Mastercard, American Express), PayPal, y pago en efectivo al recibir el pedido.'
        },
        {
          q: '¿Por qué veo dos cargos en mi tarjeta?',
          a: 'A veces tu banco hace una autorización previa y luego el cargo real. La autorización se libera en 1-3 días. Si ves dos cargos reales después de 24 horas, crea un reclamo inmediatamente.'
        },
        {
          q: '¿Cómo solicito un reembolso?',
          a: 'Los reembolsos se procesan automáticamente cuando hay problemas con tu pedido. También puedes crear un reclamo si consideras que debes recibir un reembolso.'
        }
      ]
    },
    {
      title: 'Problemas y Reclamos',
      icon: HelpCircle,
      faqs: [
        {
          q: '¿Cómo crear un reclamo?',
          a: 'Ve a "Mis pedidos", selecciona el pedido con problemas y haz clic en "Reportar problema". También puedes ir directamente a "Crear reclamo" desde el menú principal.'
        },
        {
          q: '¿Cuánto tarda en responderse un reclamo?',
          a: 'Nuestro sistema inteligente analiza tu reclamo en segundos. La mayoría de los casos reciben una respuesta en menos de 5 minutos. Casos complejos pueden tardar hasta 2 horas.'
        },
        {
          q: '¿Qué pasa si no estoy de acuerdo con la respuesta?',
          a: 'Puedes solicitar una revisión adicional desde el detalle de tu reclamo. Un supervisor revisará personalmente tu caso.'
        }
      ]
    },
    {
      title: 'Seguridad',
      icon: Shield,
      faqs: [
        {
          q: '¿Cómo protegen mis datos de pago?',
          a: 'Utilizamos encriptación de nivel bancario (SSL/TLS) y cumplimos con los estándares PCI DSS. Nunca almacenamos tus datos completos de tarjeta.'
        },
        {
          q: '¿Qué hago si detecto actividad sospechosa en mi cuenta?',
          a: 'Crea un reclamo inmediatamente seleccionando "Fraude o seguridad". Estos casos tienen prioridad máxima y se revisan de inmediato.'
        }
      ]
    }
  ];

  return (
    <ClientLayout>
      <div className="space-y-8 max-w-5xl mx-auto">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-3">Centro de Ayuda</h1>
          <p className="text-gray-600 text-lg">¿En qué podemos ayudarte?</p>
        </div>

        {/* Search */}
        <Card>
          <CardContent className="pt-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
              <Input
                placeholder="Busca una pregunta o tema..."
                className="pl-10 h-12 text-base"
              />
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6">
          <Link to="/claims/new">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardContent className="pt-6 text-center">
                <div className="size-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <HelpCircle className="size-6 text-orange-600" />
                </div>
                <h3 className="font-semibold mb-2">Crear reclamo</h3>
                <p className="text-sm text-gray-600">
                  Reporta un problema con tu pedido
                </p>
              </CardContent>
            </Card>
          </Link>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="pt-6 text-center">
              <div className="size-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageCircle className="size-6 text-blue-600" />
              </div>
              <h3 className="font-semibold mb-2">Chat en vivo</h3>
              <p className="text-sm text-gray-600">
                Chatea con nuestro equipo
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="pt-6 text-center">
              <div className="size-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mail className="size-6 text-green-600" />
              </div>
              <h3 className="font-semibold mb-2">Enviar email</h3>
              <p className="text-sm text-gray-600">
                Contacta por correo electrónico
              </p>
            </CardContent>
          </Card>
        </div>

        {/* FAQs */}
        <div>
          <h2 className="text-2xl font-bold mb-6">Preguntas frecuentes</h2>
          <div className="space-y-6">
            {faqCategories.map((category) => (
              <Card key={category.title}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <category.icon className="size-5" />
                    {category.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Accordion type="single" collapsible className="w-full">
                    {category.faqs.map((faq, index) => (
                      <AccordionItem key={index} value={`item-${index}`}>
                        <AccordionTrigger className="text-left">
                          {faq.q}
                        </AccordionTrigger>
                        <AccordionContent className="text-gray-600">
                          {faq.a}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Contact */}
        <Card className="bg-gradient-to-br from-orange-50 to-blue-50 border-orange-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-3">¿No encontraste lo que buscabas?</h3>
              <p className="text-gray-600 mb-6">
                Nuestro equipo de soporte está disponible 24/7 para ayudarte
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <Link to="/claims/new">
                  <Button className="gap-2">
                    <HelpCircle className="size-4" />
                    Crear reclamo
                  </Button>
                </Link>
                <Button variant="outline" className="gap-2">
                  <Phone className="size-4" />
                  Llamar: +34 900 123 456
                </Button>
                <Button variant="outline" className="gap-2">
                  <Mail className="size-4" />
                  soporte@smartclaim.com
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </ClientLayout>
  );
}
