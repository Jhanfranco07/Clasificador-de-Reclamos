import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ShoppingCart, ArrowLeft } from 'lucide-react';
import ClientLayout from '../../components/ClientLayout';
import { createOrder } from '../../lib/api';
import { formatCurrency } from '../../lib/utils';

const CART_KEY = 'smartclaim_pending_cart';

type PendingCartItem = {
  id: string;
  name: string;
  price: number;
  image?: string;
  restaurantName: string;
  restaurantImage?: string;
  quantity: number;
};

const readCart = (): PendingCartItem[] => {
  try {
    return JSON.parse(window.localStorage.getItem(CART_KEY) || '[]') as PendingCartItem[];
  } catch {
    return [];
  }
};

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [cart] = useState<PendingCartItem[]>(readCart);
  const [address, setAddress] = useState('Av. Primavera 123, Lima');
  const [paymentMethod, setPaymentMethod] = useState('Tarjeta');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const total = useMemo(
    () => cart.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [cart]
  );
  const restaurantName = cart[0]?.restaurantName || 'SmartClaim Delivery';
  const restaurantImage = cart[0]?.restaurantImage || cart[0]?.image;

  const handleConfirm = async () => {
    if (!cart.length) {
      setError('Agrega productos al carrito antes de confirmar el pedido.');
      return;
    }
    if (address.trim().length < 5) {
      setError('Ingresa una dirección de entrega válida.');
      return;
    }

    setError('');
    setIsSubmitting(true);
    try {
      const result = await createOrder({
        store_name: restaurantName,
        store_image: restaurantImage,
        payment_method: paymentMethod,
        delivery_address: address.trim(),
        items: cart.map((item) => ({
          name: item.name,
          quantity: item.quantity,
          price: item.price,
          image: item.image,
        })),
      });
      window.localStorage.removeItem(CART_KEY);
      navigate(`/orders/${result.order.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el pedido.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ClientLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="size-4 mr-2" />
            Volver al catálogo
          </Button>
        </Link>

        <div>
          <h1 className="text-3xl font-bold mb-2">Confirmar pedido</h1>
          <p className="text-gray-600">Revisa tu carrito, dirección y forma de pago antes de finalizar.</p>
        </div>

        {cart.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <ShoppingCart className="size-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-xl font-semibold mb-2">Tu carrito está vacío</h3>
              <p className="text-gray-600 mb-6">Vuelve al catálogo y agrega productos para continuar.</p>
              <Link to="/">
                <Button>Explorar restaurantes</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid lg:grid-cols-[1fr_340px] gap-6 items-start">
            <Card>
              <CardHeader>
                <CardTitle>Detalle del pedido</CardTitle>
                <CardDescription>{restaurantName}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {cart.map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-4 border-b pb-4 last:border-b-0 last:pb-0">
                    <div className="flex items-center gap-3">
                      {item.image && <img src={item.image} alt={item.name} className="size-14 rounded-lg object-cover" />}
                      <div>
                        <p className="font-semibold">{item.name}</p>
                        <p className="text-sm text-gray-500">Cantidad: {item.quantity}</p>
                      </div>
                    </div>
                    <p className="font-bold">{formatCurrency(item.price * item.quantity)}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Pago y entrega</CardTitle>
                <CardDescription>Total: {formatCurrency(total)}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="address">Dirección de entrega</Label>
                  <Input id="address" value={address} onChange={(event) => setAddress(event.target.value)} />
                </div>

                <div className="space-y-2">
                  <Label>Método de pago</Label>
                  <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Tarjeta">Tarjeta</SelectItem>
                      <SelectItem value="Yape">Yape</SelectItem>
                      <SelectItem value="Plin">Plin</SelectItem>
                      <SelectItem value="Efectivo">Efectivo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
                    {error}
                  </div>
                )}

                <Button onClick={handleConfirm} disabled={isSubmitting} className="w-full">
                  {isSubmitting ? 'Confirmando...' : 'Confirmar pedido'}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </ClientLayout>
  );
}
