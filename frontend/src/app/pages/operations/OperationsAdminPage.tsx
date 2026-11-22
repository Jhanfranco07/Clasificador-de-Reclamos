import { useEffect, useState } from 'react';
import { getOperations, operationalWrite, OperationsOverview, ManagedUser, ManagedRestaurant } from '../../lib/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import AdminLayout from '../../components/AdminLayout';

export default function OperationsAdminPage() {
  const [data, setData] = useState<OperationsOverview | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [restaurant, setRestaurant] = useState('');
  const [operator, setOperator] = useState('');
  const [edit, setEdit] = useState(false);
  const [active, setActive] = useState(true);
  const [reason, setReason] = useState('');
  const load = async () => {
    setError('');
    setData(null);
    try { setData(await getOperations()); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo cargar la administración.'); }
  };
  useEffect(() => { void load(); }, []);
  async function save(path: string, payload: object, method = 'PATCH') {
    setBusy(true); setError('');
    try { await operationalWrite(path, { ...payload, request_id: crypto.randomUUID() }, method); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo guardar.'); }
    finally { setBusy(false); }
  }
  return <AdminLayout><div className="space-y-6 min-w-0 break-words">
    <h1 className="font-bold text-2xl">Comercios, roles y operadores</h1>
    <p>Las cuentas se registran inicialmente como CLIENT. El administrador concede el rol y los establecimientos expresamente.</p>
    {error && <p role="alert" className="text-red-700">{error}</p>}<Button className="max-w-full h-auto whitespace-normal" disabled={busy} onClick={load}>Actualizar</Button>
    {!data ? <p>Cargando administración...</p> : <>
      <section className="space-y-3"><h2 className="font-semibold text-xl">Usuarios y roles</h2>{data.users.map(user => <UserEditor key={user.id_auth_user} user={user} busy={busy} save={payload => save(`/api/operations/users/${user.id_auth_user}`, payload)} />)}</section>
      <section className="space-y-3"><h2 className="font-semibold text-xl">Establecimientos</h2>{data.restaurants.map(store => <RestaurantEditor key={store.id_restaurante} store={store} busy={busy} save={payload => save(`/api/operations/restaurants/${store.id_restaurante}`, payload)} />)}</section>
      <Card><CardContent className="pt-6 space-y-3"><h2 className="font-semibold text-xl">Autorizar operador</h2>
        <label className="block" htmlFor="operator-restaurant">Establecimiento</label><select id="operator-restaurant" className="border p-2 rounded w-full min-w-0 max-w-full" value={restaurant} onChange={e => setRestaurant(e.target.value)}><option value="">Seleccionar establecimiento</option>{data.restaurants.map(r => <option key={r.id_restaurante} value={r.id_restaurante}>{r.nombre}</option>)}</select>
        <label className="block" htmlFor="operator-user">Operador MERCHANT</label><select id="operator-user" className="border p-2 rounded w-full min-w-0 max-w-full" value={operator} onChange={e => setOperator(e.target.value)}><option value="">Seleccionar operador</option>{data.users.filter(u => u.rol === 'MERCHANT' && u.estado === 'ACTIVO').map(u => <option key={u.id_auth_user} value={u.id_auth_user}>{u.nombre} · {u.correo}</option>)}</select>
        <label className="flex gap-2"><input type="checkbox" checked={edit} onChange={e => setEdit(e.target.checked)} />Permitir editar productos</label>
        <label className="flex gap-2"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />Autorización activa</label>
        <label className="block">Motivo de autorización<textarea className="border rounded w-full p-2" value={reason} onChange={e => setReason(e.target.value)} /></label>
        <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !restaurant || !operator || !reason.trim()} onClick={() => save(`/api/operations/restaurants/${restaurant}/operator`, { user_id: Number(operator), active, edit_products: edit, reason }, 'PUT')}>Guardar autorización</Button>
        <ul>{data.operators.map(o => <li key={`${o.id_auth_user}-${o.id_restaurante}`}>Usuario {o.id_auth_user} · Establecimiento {o.id_restaurante} · {o.activo ? 'Activo' : 'Revocado'} · Edición {o.puede_editar_productos ? 'habilitada' : 'deshabilitada'}</li>)}</ul>
      </CardContent></Card>
      <section className="space-y-2"><h2 className="font-semibold text-xl">Auditoría administrativa reciente</h2>{data.audit.map(a => <article key={a.request_id} className="border rounded p-3"><p>{a.accion} · Recurso {a.recurso_id} · {a.actor_nombre} ({a.actor_rol}) · {a.fecha}</p><p className="break-all">{a.detalle}</p></article>)}</section>
    </>}
  </div></AdminLayout>;
}

function UserEditor({ user, busy, save }: { user: ManagedUser; busy: boolean; save: (data: object) => void }) {
  const [role, setRole] = useState(user.rol);
  const [active, setActive] = useState(user.estado === 'ACTIVO');
  const [reason, setReason] = useState('');
  return <Card><CardContent className="pt-4 space-y-3"><h3 className="font-semibold">{user.nombre}</h3><p>{user.correo}</p>
    <label className="block">Rol de {user.nombre}<select className="border p-2 rounded w-full min-w-0 max-w-full" value={role} onChange={e => setRole(e.target.value as ManagedUser['rol'])}>{['CLIENT', 'AGENT', 'ADMIN', 'MERCHANT', 'COURIER'].map(r => <option key={r}>{r}</option>)}</select></label>
    <label className="flex gap-2"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />Cuenta activa</label>
    <label className="block">Motivo para {user.nombre}<input className="border rounded w-full p-2" value={reason} onChange={e => setReason(e.target.value)} /></label>
    <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !reason.trim()} onClick={() => save({ role, active, reason })}>Guardar rol de {user.nombre}</Button>
  </CardContent></Card>;
}

function RestaurantEditor({ store, busy, save }: { store: ManagedRestaurant; busy: boolean; save: (data: object) => void }) {
  const [address, setAddress] = useState(store.direccion || '');
  const [responsible, setResponsible] = useState(store.responsable || '');
  const [active, setActive] = useState(Boolean(store.activo));
  return <Card><CardContent className="pt-4 space-y-3"><h3 className="font-semibold">{store.nombre}</h3>
    <label className="block">Dirección de {store.nombre}<input className="border rounded w-full p-2" value={address} onChange={e => setAddress(e.target.value)} /></label>
    <label className="block">Responsable de {store.nombre}<input className="border rounded w-full p-2" value={responsible} onChange={e => setResponsible(e.target.value)} /></label>
    <label className="flex gap-2"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />Establecimiento activo</label>
    <Button className="max-w-full h-auto whitespace-normal" disabled={busy || !address.trim() || !responsible.trim()} onClick={() => save({ address, responsible, active })}>Guardar establecimiento {store.nombre}</Button>
  </CardContent></Card>;
}
