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
import { ArrowRight, Check, ChefHat, Package, RefreshCw, Search, Store, UtensilsCrossed } from 'lucide-react';

export function OperationsLayout({ children }: { children: ReactNode }) {
  const { currentUser, logout } = useAuth();
  if (currentUser?.role === 'ADMIN') return <AdminLayout>{children}</AdminLayout>;
  return <div className="min-h-screen bg-background text-foreground">
    <header className="bg-slate-950 text-white p-4 flex flex-wrap gap-4 items-center justify-between">
      <Link to={currentUser?.role === 'MERCHANT' ? '/merchant' : '/courier'} className="font-bold">SmartClaim AI · {currentUser?.role === 'MERCHANT' ? 'Comercio' : 'Repartidor'}</Link>
      <span className="break-all">{currentUser?.name}</span><NotificationBell /><Button className="max-w-full h-auto whitespace-normal" onClick={logout}>Cerrar sesión</Button>
    </header><main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-9 lg:px-8">{children}</main>
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
  const [productSearch, setProductSearch] = useState('');
  const [productAvailability, setProductAvailability] = useState<'ALL' | 'AVAILABLE' | 'UNAVAILABLE'>('ALL');
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
  const filteredOrders = orders.filter(item => filter === 'ALL' || item.status === filter);
  const availableProducts = products.filter(item => Boolean(item.disponible)).length;
  const filteredProducts = products.filter(item => {
    const queryMatches = `${item.nombre} ${item.restaurante}`.toLocaleLowerCase('es').includes(productSearch.trim().toLocaleLowerCase('es'));
    const statusMatches = productAvailability === 'ALL' || Boolean(item.disponible) === (productAvailability === 'AVAILABLE');
    return queryMatches && statusMatches;
  });
  const transition = (state: string) => order && act(`/api/orders/${order.id}/transition`, { state, expected_version: order.version, reason: reason || undefined });

  return <OperationsLayout><div className="space-y-5 min-w-0 break-words">
    <div className="overflow-hidden rounded-3xl bg-slate-950 px-5 py-6 text-white shadow-sm sm:px-8 sm:py-8">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="flex min-w-0 items-start gap-4">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-orange-500/15 text-orange-400"><Store size={24} aria-hidden="true" /></div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-300">{role === 'MERCHANT' ? 'Panel del comercio' : role === 'COURIER' ? 'Panel de repartos' : 'Operaciones'}</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">{role === 'COURIER' ? 'Entregas asignadas' : 'Gestión de pedidos'}</h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-300">Administra los pedidos y consulta su historial de operaciones. El pago no implica verificación bancaria.</p>
          </div>
        </div>
        <Button variant="outline" className="h-10 gap-2 rounded-xl border-white/25 bg-white/10 text-white hover:bg-white/20 hover:text-white" disabled={loading || busy} onClick={load}><RefreshCw size={16} aria-hidden="true" />Actualizar</Button>
      </div>
      {!id && !loading && <div className="mt-7 grid grid-cols-2 gap-3 sm:max-w-xl sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 sm:p-4"><p className="text-xs text-slate-300">Pedidos visibles</p><p className="mt-1 text-2xl font-bold tabular-nums">{orders.length}</p></div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 sm:p-4"><p className="text-xs text-slate-300">En curso</p><p className="mt-1 text-2xl font-bold tabular-nums">{orders.filter(item => !['DELIVERED', 'CANCELLED'].includes(item.status)).length}</p></div>
        {role === 'MERCHANT' && <div className="col-span-2 rounded-2xl border border-white/10 bg-white/5 p-3 sm:col-span-1 sm:p-4"><p className="text-xs text-slate-300">Platos disponibles</p><p className="mt-1 text-2xl font-bold tabular-nums">{availableProducts}<span className="ml-1 text-sm font-normal text-slate-300">/ {products.length}</span></p></div>}
      </div>}
    </div>
    {error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
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
      <section aria-label="Listado de pedidos" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-xl font-bold tracking-tight text-slate-900">Pedidos <span className="ml-1 text-sm font-medium text-slate-500">({filteredOrders.length})</span></h2><p className="mt-1 text-sm text-slate-500">Consulta el estado y continúa con el siguiente paso.</p></div>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-600">Estado
            <select aria-label="Filtrar pedidos por estado" className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500" value={filter} onChange={e => setFilter(e.target.value)}><option value="ALL">Todos</option>{Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          </label>
        </div>
        {filteredOrders.length ? <div className="grid gap-4 md:grid-cols-2">{filteredOrders.map(item => (
          <Card key={item.id} className="overflow-hidden rounded-2xl border-slate-200 shadow-sm transition-shadow hover:shadow-md">
            <CardContent className="flex h-full flex-col gap-4 p-5 sm:p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3"><span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-600"><Package size={21} aria-hidden="true" /></span>
                  <div className="min-w-0"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Pedido</p><h3 className="break-all text-base font-bold text-slate-900">{item.code}</h3></div>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${item.status === 'DELIVERED' ? 'bg-emerald-50 text-emerald-700' : item.status === 'CANCELLED' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-800'}`}>{ORDER_STATUS_LABELS[item.status]}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600"><Store size={16} className="shrink-0 text-slate-400" aria-hidden="true" /><span className="truncate">{item.storeName}</span></div>
              <div className="mt-auto flex flex-wrap items-end justify-between gap-3 border-t border-slate-100 pt-4">
                <div><p className="text-xs text-slate-500">{item.items.length} productos · Total registrado</p><p className="text-lg font-bold tabular-nums text-slate-900">S/ {item.total.toFixed(2)}</p></div>
                <Button className="h-10 gap-2 rounded-xl bg-orange-600 px-4 text-white hover:bg-orange-700" asChild><Link to={`${root === '/admin/orders' ? '/admin' : root}/orders/${item.id}`}>Ver pedido <ArrowRight size={16} aria-hidden="true" /></Link></Button>
              </div>
            </CardContent>
          </Card>
        ))}</div> : <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center"><Package className="mx-auto text-slate-400" size={28} aria-hidden="true" /><p className="mt-3 font-medium text-slate-700">{orders.length ? 'No hay pedidos con ese estado.' : 'Todavía no hay pedidos asignados a esta cuenta.'}</p><p className="mt-1 text-sm text-slate-500">Los pedidos autorizados aparecerán aquí.</p></div>}
      </section>
      {role === 'MERCHANT' && <section className="space-y-5 border-t border-slate-200 pt-7" aria-label="Gestión de productos">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div><p className="mb-1 text-xs font-bold uppercase tracking-[0.15em] text-orange-600">Catálogo del comercio</p><h2 className="text-2xl font-bold tracking-tight text-slate-900">Mis productos</h2><p className="mt-1 text-sm text-slate-500">Actualiza precios y disponibilidad de los platos que tienes autorizados.</p></div>
          <div className="flex items-center gap-2 rounded-xl bg-orange-50 px-4 py-2 text-sm font-semibold text-orange-800"><ChefHat size={18} aria-hidden="true" />{products.length} productos</div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="relative flex-1"><span className="sr-only">Buscar platos</span><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} aria-hidden="true" /><input type="search" value={productSearch} onChange={e => setProductSearch(e.target.value)} placeholder="Buscar plato o restaurante..." className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500" /></label>
          <label className="flex items-center gap-2 text-sm text-slate-600"><span className="sr-only">Filtrar disponibilidad</span><select value={productAvailability} onChange={e => setProductAvailability(e.target.value as 'ALL' | 'AVAILABLE' | 'UNAVAILABLE')} className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500 sm:w-48"><option value="ALL">Todos los productos</option><option value="AVAILABLE">Disponibles</option><option value="UNAVAILABLE">No disponibles</option></select></label>
        </div>
        {filteredProducts.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filteredProducts.map(product => <ProductEditor key={product.id_producto} product={product} busy={busy} save={data => act(`/api/operations/products/${product.id_producto}`, data, 'PATCH')} />)}</div> : <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-center"><UtensilsCrossed size={28} className="mx-auto text-slate-400" aria-hidden="true" /><p className="mt-3 font-medium text-slate-700">{products.length ? 'No encontramos productos con esos filtros.' : 'No tienes productos autorizados todavía.'}</p><p className="mt-1 text-sm text-slate-500">{products.length ? 'Prueba otra búsqueda o disponibilidad.' : 'El administrador debe vincularte con un establecimiento.'}</p></div>}
      </section>}
    </> : null}
  </div></OperationsLayout>;
}

function ProductEditor({ product, busy, save }: { product: ManagedProduct; busy: boolean; save: (data: object) => void }) {
  const [name, setName] = useState(product.nombre);
  const [price, setPrice] = useState(String(product.precio));
  const [available, setAvailable] = useState(Boolean(product.disponible));
  useEffect(() => {
    setName(product.nombre);
    setPrice(String(product.precio));
    setAvailable(Boolean(product.disponible));
  }, [product.nombre, product.precio, product.disponible]);
  const editable = Boolean(product.puede_editar_productos);
  const changed = name !== product.nombre || Number(price) !== Number(product.precio) || available !== Boolean(product.disponible);
  const valid = name.trim().length > 0 && price.trim() !== '' && Number.isFinite(Number(price)) && Number(price) >= 0;
  return <Card className="overflow-hidden rounded-2xl border-slate-200 shadow-sm transition-all hover:shadow-md">
    <CardContent className="flex h-full flex-col gap-4 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-orange-50 text-orange-600">
          {product.imagen ? <img src={product.imagen} alt={product.nombre} loading="lazy" className="size-full object-cover" /> : <UtensilsCrossed size={27} aria-hidden="true" />}
        </div>
        <div className="min-w-0 flex-1"><p className="truncate text-xs font-medium text-slate-500">{product.restaurante}</p><h3 className="mt-1 line-clamp-2 text-base font-bold leading-snug text-slate-900">{product.nombre}</h3><p className="mt-1 text-sm font-bold tabular-nums text-orange-700">S/ {Number(product.precio).toFixed(2)}</p></div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-y border-slate-100 py-3">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${available ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{available ? 'Disponible' : 'No disponible'}</span>
        {!editable && <span className="text-xs text-slate-500">Solo lectura</span>}
        {changed && editable && <span className="text-xs font-medium text-amber-700">Cambios sin guardar</span>}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="space-y-1.5 text-xs font-semibold text-slate-600 sm:col-span-2">Nombre del plato<input value={name} disabled={!editable || busy} maxLength={140} onChange={event => setName(event.target.value)} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900 disabled:bg-slate-50 disabled:text-slate-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500" /></label>
        <label className="space-y-1.5 text-xs font-semibold text-slate-600">Precio (S/)<input type="number" min="0" step="0.01" value={price} disabled={!editable || busy} onChange={event => setPrice(event.target.value)} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900 disabled:bg-slate-50 disabled:text-slate-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500" /></label>
        <label className="flex items-end gap-2 pb-2 text-xs font-semibold text-slate-600"><input type="checkbox" checked={available} disabled={!editable || busy} onChange={event => setAvailable(event.target.checked)} className="size-4 accent-orange-600" /> A la venta</label>
      </div>
      {editable && <Button className="mt-auto h-10 w-full gap-2 rounded-xl bg-orange-600 text-white hover:bg-orange-700 disabled:bg-slate-100 disabled:text-slate-400" disabled={busy || !changed || !valid} onClick={() => save({ name: name.trim(), price: Number(price), available })}><Check size={17} aria-hidden="true" />{busy ? 'Guardando...' : changed ? 'Guardar cambios' : 'Sin cambios pendientes'}</Button>}
    </CardContent>
  </Card>;
}
