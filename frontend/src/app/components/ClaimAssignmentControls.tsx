import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { assignClaim, escalateClaim, listClaimAssignees, ClaimDetailResponse } from '../lib/api';
import { Button } from './ui/button';

export default function ClaimAssignmentControls({ detail, onChange }: {
  detail: ClaimDetailResponse;
  onChange: (detail: ClaimDetailResponse) => void;
}) {
  const { currentUser } = useAuth();
  const assignment = detail.claim.assignment;
  const [assignees, setAssignees] = useState<Array<{ id: number; name: string; role: string }>>([]);
  const [selected, setSelected] = useState('');
  const [destination, setDestination] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [retry, setRetry] = useState(0);
  const requestId = useMemo(() => crypto.randomUUID(), [detail.claim.id, assignment?.version, reason, selected, destination]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listClaimAssignees().then(result => {
      if (active) { setAssignees(result.items); setError(''); }
    }).catch(err => {
      if (active) setError(err instanceof Error ? err.message : 'No se pudieron consultar responsables.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retry]);

  async function run(escalate: boolean) {
    if (!assignment) return;
    setWorking(true);
    setError('');
    try {
      const payload = { expected_version: assignment.version, reason: reason.trim(), request_id: `${requestId}:${escalate ? 'escalate' : 'assign'}` };
      const result = escalate
        ? await escalateClaim(detail.claim.id, { ...payload, assignee_id: destination ? Number(destination) : undefined })
        : await assignClaim(detail.claim.id, { ...payload, assignee_id: currentUser?.role === 'ADMIN' ? Number(selected) : Number(currentUser?.id) });
      onChange(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo confirmar la asignación. Recarga el caso si cambió.');
    } finally { setWorking(false); }
  }

  const closed = detail.claim.statusKey === 'CLOSED';
  const canEscalate = currentUser?.role === 'ADMIN' || !assignment?.active || assignment.id === Number(currentUser?.id);
  const disabled = loading || working || closed || !assignment || !assignees.length || !reason.trim();

  return <section aria-label="Responsable del reclamo" className="rounded-lg border p-4 space-y-3 break-words">
    <h2 className="text-lg font-bold">Responsable del reclamo</h2>
    <p>{assignment?.id ? `${assignment.name} · ID ${assignment.id}` : 'Sin responsable autenticado asignado'}</p>
    {assignment?.assignedAt && <p>Asignado el {assignment.assignedAt}</p>}
    {assignment?.id && !assignment.active && <p>El responsable está inactivo o cambió de rol. El caso requiere reasignación.</p>}
    {!assignment?.id && assignment?.name && <p className="text-sm text-muted-foreground">Referencia histórica conservada · {assignment.name}</p>}
    {loading && <p role="status">Cargando responsables...</p>}
    {error && <div role="alert"><p>{error}</p><Button variant="outline" onClick={() => setRetry(value => value + 1)}>Reintentar responsables</Button></div>}
    {currentUser?.role === 'ADMIN' && <>
      <label htmlFor="claim-assignee" className="block">Asignar responsable activo</label>
      <select id="claim-assignee" className="border rounded p-2 w-full min-w-0" value={selected} onChange={event => setSelected(event.target.value)} disabled={working || loading || closed}>
        <option value="">Seleccionar responsable</option>
        {assignees.map(user => <option key={user.id} value={user.id}>{user.name} ({user.role})</option>)}
      </select>
    </>}
    <label htmlFor="assignment-reason" className="block">Motivo de asignación o escalamiento</label>
    <textarea id="assignment-reason" className="border rounded p-2 w-full" value={reason} onChange={event => setReason(event.target.value)} disabled={working || closed} maxLength={1000} />
    <Button disabled={disabled || currentUser?.role === 'ADMIN' && !selected || currentUser?.role === 'AGENT' && assignment?.active}
      onClick={() => void run(false)}>{currentUser?.role === 'ADMIN' ? 'Confirmar asignación' : 'Asumir caso'}</Button>
    <label htmlFor="escalation-destination" className="block">Destinatario del escalamiento</label>
    <select id="escalation-destination" className="border rounded p-2 w-full min-w-0" value={destination} onChange={event => setDestination(event.target.value)} disabled={working || loading || closed}>
      <option value="">ADMIN activo seleccionado por el servidor</option>
      {assignees.filter(user => user.role === 'ADMIN').map(user => <option key={user.id} value={user.id}>{user.name}</option>)}
    </select>
    <Button variant="destructive" disabled={disabled || !canEscalate || detail.claim.statusKey === 'ESCALATED'} onClick={() => void run(true)}>Escalar con motivo</Button>
  </section>;
}
