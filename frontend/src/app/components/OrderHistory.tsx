import { ApiOrder } from '../lib/api';
import { ORDER_STATUS_LABELS } from '../types';

export default function OrderHistory({ order }: { order: ApiOrder }) {
  return <section aria-label="Historial del pedido" className="space-y-2">
    <h2 className="font-semibold text-xl">Historial del pedido</h2>
    {!order.events?.length && <p>Sin eventos operativos registrados. Pedido histórico.</p>}
    {order.events?.map((event, index) => <div key={index} className="border-l-2 pl-3 break-words">
      <p>{event.accion === 'DELAY_REPORTED' ? 'Demora registrada' : event.accion} · {ORDER_STATUS_LABELS[event.estado_nuevo as ApiOrder['status']] || event.estado_nuevo}</p>
      <p className="text-sm text-muted-foreground">{event.fecha} {event.actor_nombre && `· ${event.actor_nombre} (${event.actor_rol})`}</p>
      {event.motivo && <p>{event.motivo}</p>}
      {event.courier_id && <p>Repartidor ID {event.courier_id}</p>}
    </div>)}
  </section>;
}
