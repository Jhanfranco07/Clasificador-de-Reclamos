import { useEffect, useState } from 'react';
import { MessageSquare, Send } from 'lucide-react';
import { ClaimMessage, listClaimMessages, sendClaimMessage } from '../lib/api';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { formatDateTime } from '../lib/utils';
import { toast } from 'sonner';

export default function ClaimConversation({
  claimId,
  viewer,
  closed,
}: {
  claimId: string;
  viewer: 'client' | 'agent';
  closed: boolean;
}) {
  const [messages, setMessages] = useState<ClaimMessage[]>([]);
  const [message, setMessage] = useState('');
  const [working, setWorking] = useState(false);

  const load = () => listClaimMessages(claimId).then((result) => setMessages(result.items));

  useEffect(() => {
    load().catch(() => setMessages([]));
  }, [claimId]);

  const send = async () => {
    if (message.trim().length < 2) return;
    setWorking(true);
    try {
      const result = await sendClaimMessage(claimId, message.trim());
      setMessages(result.items);
      setMessage('');
      toast.success(viewer === 'client' ? 'Mensaje enviado a soporte.' : 'Mensaje enviado al cliente.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo enviar el mensaje.');
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className="rounded-lg border bg-white p-5">
      <div className="mb-5 flex items-center gap-2">
        <MessageSquare className="size-5 text-orange-600" />
        <h2 className="text-lg font-bold">Conversación del reclamo</h2>
      </div>
      <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
        {messages.map((item) => {
          const own = item.senderType === viewer;
          return (
            <div key={item.id} className={`flex ${own ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-lg px-4 py-3 ${own ? 'bg-slate-900 text-white' : 'bg-gray-100 text-gray-900'}`}>
                <p className="whitespace-pre-line text-sm">{item.message}</p>
                <p className={`mt-2 text-xs ${own ? 'text-white/65' : 'text-gray-500'}`}>
                  {item.senderType === 'client' ? 'Cliente' : item.senderType === 'agent' ? 'Soporte' : 'Sistema'} · {formatDateTime(item.createdAt)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      {closed ? (
        <p className="mt-5 rounded-md bg-gray-50 p-3 text-sm text-gray-600">
          Este reclamo está cerrado. Reábrelo para continuar la conversación.
        </p>
      ) : (
        <div className="mt-5 space-y-3 border-t pt-4">
          <Textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={viewer === 'client' ? 'Escribe información adicional para soporte...' : 'Escribe una respuesta para el cliente...'}
          />
          <Button disabled={working || message.trim().length < 2} onClick={send} className="gap-2">
            <Send className="size-4" />
            Enviar mensaje
          </Button>
        </div>
      )}
    </section>
  );
}
