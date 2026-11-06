import { useEffect, useState } from 'react';
import { ApiOrder, getClaimOrderContext } from '../lib/api';
import { Button } from './ui/button';
import OrderHistory from './OrderHistory';
import { ORDER_STATUS_LABELS } from '../types';

export default function ClaimOrderContext({ claimId }: { claimId: string }) {
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    getClaimOrderContext(claimId).then(data => { if (active) setOrder(data.order); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Error al consultar el pedido.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [claimId, attempt]);
  return <section className="border rounded p-4 space-y-3 break-words" aria-label="Contexto verificado del pedido">
    <h2 className="font-semibold text-xl">Contexto verificado del pedido</h2>
    {loading ? <p>Cargando contexto...</p> : error ? <><p role="alert">{error}</p><Button onClick={() => setAttempt(a => a + 1)}>Reintentar contexto</Button></> : order ? <>
      <p>{order.code} · {order.storeName} · {ORDER_STATUS_LABELS[order.status]}</p>
      <ul>{order.items.map(item => <li key={item.id}>{item.quantity} × {item.name} · S/ {item.price.toFixed(2)}</li>)}</ul>
      <p>Pago y devoluciones no verificados.</p><OrderHistory order={order} />
    </> : <p>Pedido histórico sin referencia conciliada. El contexto operativo es desconocido.</p>}
  </section>;
}
