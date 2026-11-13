import { useEffect, useRef, useState, ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { useAuth } from '../../contexts/AuthContext';
import AdminLayout from '../../components/AdminLayout';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { ApiOrder, getOrder, listOrders, operationalWrite, getOperations, getAvailability, getOperationalProducts, ManagedProduct, OperationsOverview } from '../../lib/api';
import { ORDER_STATUS_LABELS } from '../../types';
import OrderHistory from '../../components/OrderHistory';
import NotificationBell from '../../components/NotificationBell';

export function OperationsLayout({ children }: { children: ReactNode }) {
  const { currentUser, logout } = useAuth();
  if (currentUser?.role === 'ADMIN') return <AdminLayout>{children}</AdminLayout>;
  return <div className="min-h-screen bg-background text-foreground">
    <header className="bg-slate-950 text-white p-4 flex flex-wrap gap-4 items-center justify-between">
      <Link to={currentUser?.role === 'MERCHANT' ? '/merchant' : '/courier'} className="font-bold">SmartClaim AI · {currentUser?.role === 'MERCHANT' ? 'Comercio' : 'Repartidor'}</Link>
      <span className="break-all">{currentUser?.name}</span><NotificationBell /><Button className="max-w-full h-auto whitespace-normal" onClick={logout}>Cerrar sesión</Button>
    </header><main className="container mx-auto p-4 max-w-6xl">{children}</main>
  </div>;
}


export default function OperationsPage() {
  const { currentUser } = useAuth();
  const { id } = useParams();
  const role = currentUser?.role;
  const root = role === 'MERCHANT' ? '/merchant' : role === 'COURIER' ? '/courier' : '/admin/orders';
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [overview, setOverview] = useState<OperationsOverview | null>(null);
  const [products, setProducts] = useState<ManagedProduct[]>([]);
  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState('');
  const [courier, setCourier] = useState('');
  const [filter, setFilter] = useState('ALL');
  const loadGeneration = useRef(0);

  async function load() {
    const generation = ++loadGeneration.current;
    setLoading(true);
    setError('');
    setOrder(null);
    try {
      const [detail, listing, administration, availability, catalog] = await Promise.all([
        id ? getOrder(id) : Promise.resolve(null),
        id ? Promise.resolve(null) : listOrders(),
        role === 'ADMIN' ? getOperations() : Promise.resolve(null),
        role === 'COURIER' ? getAvailability() : Promise.resolve(null),
        role === 'MERCHANT' ? getOperationalProducts() : Promise.resolve(null),
      ]);
      if (generation !== loadGeneration.current) return;
      setOrder(detail?.order ?? null);
      setOrders(listing?.items ?? []);
      setOverview(administration);
      setAvailable(availability?.available ?? false);
      setProducts(catalog?.items ?? []);
    } catch (err) {
      if (generation === loadGeneration.current) {
        setError(err instanceof Error ? err.message : 'No se pudo cargar la operación.');
      }
    } finally {
      if (generation === loadGeneration.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
    return () => { loadGeneration.current += 1; };
  }, [id, role]);

  async function act(path: string, data: object, method = 'POST') {
    setBusy(true);
    setError('');
    try {
      await operationalWrite(path, { ...data, request_id: crypto.randomUUID() }, method);
      await load();
      setReason('');
    } catch (err) { setError(err instanceof Error ? err.message : 'No se pudo confirmar la operación.'); }
    finally { setBusy(false); }
  }

  const next = order && ({ RECEIVED: 'ACCEPTED', ACCEPTED: 'PREPARING', PREPARING: 'READY_FOR_PICKUP', READY_FOR_PICKUP: 'IN_TRANSIT', IN_TRANSIT: 'DELIVERED' } as Record<string, string>)[order.status];
  const canTransition = order && (role === 'ADMIN' || role === 'MERCHANT' && ['RECEIVED', 'ACCEPTED', 'PREPARING'].includes(order.status) || role === 'COURIER' && ['READY_FOR_PICKUP', 'IN_TRANSIT'].includes(order.status));
  const transition = (state: string) => order && act(`/api/orders/${order.id}/transition`, { state, expected_version: order.version, reason: reason || undefined });

  return <OperationsLayout><div className="space-y-5 min-w-0 break-words">
    <h1 className="text-2xl font-bold">{role === 'COURIER' ? 'Entregas asignadas' : 'Gestión de pedidos'}</h1>
    <p className="text-sm text-muted-foreground">Estados registrados por operadores. Pago sin verificación bancaria. Seguimiento por eventos.</p>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <Button className="max-w-full h-auto whitespace-normal" variant="outline" disabled={busy} onClick={load}>Actualizar</Button>
    {loading ? <p>Cargando operación...</p> : error ? null : id && order ? <Card><CardContent className="pt-6 space-y-5">
      <Link to={root}>Volver al listado</Link>
      <h2 className="text-xl font-bold">{order.code}</h2><p>{order.storeName} · Establecimiento {order.restaurantId ?? 'pendiente de conciliación'}</p>
      <p>Estado actual · <strong>{ORDER_STATUS_LABELS[order.status]}</strong></p>
      {order.reconciliationRequired && <p>Referencia o fase histórica pendiente de conciliación. Se conserva el registro original.</p>}
      <p>Recogida · {order.pickupAddress || 'Dirección del establecimiento pendiente de registro'}</p>
      <p>Entrega · {order.deliveryAddress}</p>{order.deliveryNotes && <p>{order.deliveryNotes}</p>}
      {role !== 'COURIER' && <ul>{order.items?.map(item => <li key={item.id}>{item.quantity} × {item.name} · S/ {item.price.toFixed(2)}</li>)}</ul>}
      {(role === 'ADMIN' || role === 'MERCHANT') && <label className="block">Motivo de intervención o rechazo
        <textarea className="border rounded w-full p-2" value={reason} onChange={e => setReason(e.target.value)} /></label>}
      <div className="flex flex-wrap gap-3">
        {canTransition && next && <Button className="max-w-full h-auto whitespace-normal" disabled={busy || role === 'ADMIN' && !reason.trim()} onClick={() => transition(next)}>{next === 'IN_TRANSIT' ? 'Confirmar recogida y salida' : next === 'DELIVERED' ? 'Confirmar entrega' : ORDER_STATUS_LABELS[next as ApiOrder['status']]}</Button>}
        {(role === 'MERCHANT' && order.status === 'RECEIVED' || role === 'ADMIN' && !['CANCELLED', 'DELIVERED'].includes(order.status)) && <Button className="max-w-full h-auto whitespace-normal" variant="destructive" disabled={busy || !reason.trim()} onClick={() => transition('CANCELLED')}>Cancelar con motivo</Button>}
        {role === 'ADMIN' && order.status === 'DELAYED' && <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !reason.trim()} onClick={() => transition('PREPARING')}>Conciliar fase en preparación</Button>}
        {(role === 'ADMIN' || role === 'MERCHANT') && !['CANCELLED', 'DELIVERED'].includes(order.status) && <Button className="max-w-full h-auto whitespace-normal" variant="outline" disabled={busy || !reason.trim()} onClick={() => act(`/api/orders/${order.id}/delay`, { expected_version: order.version, reason })}>Registrar demora</Button>}
      </div>
      {role === 'ADMIN' && order.status === 'READY_FOR_PICKUP' && <section className="space-y-3">
        <label className="block">Repartidor disponible<select className="border rounded w-full p-2" value={courier} onChange={e => setCourier(e.target.value)}><option value="">Seleccionar</option>
          {overview?.couriers.filter(c => c.estado === 'ACTIVO' && c.disponible && !c.active_deliveries).map(c => <option key={c.id_auth_user} value={c.id_auth_user}>{c.nombre}</option>)}</select></label>
        <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !courier || !reason.trim()} onClick={() => act(`/api/orders/${order.id}/assignment`, { courier_id: Number(courier), expected_version: order.version, reason })}>Asignar repartidor</Button>
      </section>}
      <OrderHistory order={order} />
    </CardContent></Card> : !id && !error ? <>
      {role === 'COURIER' && <Button className="max-w-full h-auto whitespace-normal" disabled={busy} onClick={() => act('/api/operations/availability', { available: !available }, 'PUT')}>{available ? 'Disponible · pasar a no disponible' : 'No disponible · habilitar disponibilidad'}</Button>}
      <label className="block">Filtrar pedidos<select className="border rounded p-2 ml-2 max-w-full" value={filter} onChange={e => setFilter(e.target.value)}><option value="ALL">Todos</option>{Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {!orders.length && <p>No hay pedidos autorizados para esta cuenta.</p>}
      <div className="grid md:grid-cols-2 gap-4">{orders.filter(o => filter === 'ALL' || o.status === filter).map(o => <Card key={o.id}><CardContent className="pt-6 space-y-2">
        <h2 className="font-semibold">{o.code}</h2><p>{o.storeName}</p><p>{ORDER_STATUS_LABELS[o.status]}</p><Button className="max-w-full h-auto whitespace-normal" asChild><Link to={`${root === '/admin/orders' ? '/admin' : root}/orders/${o.id}`}>Ver pedido</Link></Button>
      </CardContent></Card>)}</div>
      {role === 'MERCHANT' && <section className="space-y-3"><h2 className="text-xl font-semibold">Productos autorizados</h2>{products.map(product => <ProductEditor key={product.id_producto} product={product} busy={busy} save={data => act(`/api/operations/products/${product.id_producto}`, data, 'PATCH')} />)}</section>}
    </> : null}
  </div></OperationsLayout>;
}

function ProductEditor({ product, busy, save }: { product: ManagedProduct; busy: boolean; save: (data: object) => void }) {
  const [name, setName] = useState(product.nombre);
  const [price, setPrice] = useState(String(product.precio));
  const [available, setAvailable] = useState(Boolean(product.disponible));
  return <Card><CardContent className="pt-4 space-y-3"><p>{product.restaurante}</p>
    <label className="block">Producto<input className="border rounded w-full p-2" value={name} disabled={!product.puede_editar_productos} onChange={e => setName(e.target.value)} /></label>
    <label className="block">Precio<input className="border rounded w-full p-2" type="number" min="0" step="0.01" value={price} disabled={!product.puede_editar_productos} onChange={e => setPrice(e.target.value)} /></label>
    <label className="flex gap-2"><input type="checkbox" checked={available} disabled={!product.puede_editar_productos} onChange={e => setAvailable(e.target.checked)} />Disponible</label>
    {Boolean(product.puede_editar_productos) && <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !name.trim() || !Number.isFinite(Number(price)) || Number(price) < 0} onClick={() => save({ name, price: Number(price), available })}>Guardar producto</Button>}
  </CardContent></Card>;
}
