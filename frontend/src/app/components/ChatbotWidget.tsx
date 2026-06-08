import { useState } from 'react';
import { Bot, Send, X } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { sendChatMessage } from '../lib/api';

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'bot'; text: string }>>([
    { role: 'bot', text: 'Hola. Puedo orientarte sobre pedidos, pagos y reclamos.' },
  ]);
  const [working, setWorking] = useState(false);

  const send = async () => {
    if (text.trim().length < 2) return;
    const value = text.trim();
    setText('');
    setMessages((items) => [...items, { role: 'user', text: value }]);
    setWorking(true);
    try {
      const result = await sendChatMessage(value);
      setMessages((items) => [...items, { role: 'bot', text: result.message }]);
    } catch {
      setMessages((items) => [...items, { role: 'bot', text: 'No pude conectarme ahora. Intenta nuevamente en unos segundos.' }]);
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-[120]">
      {open && (
        <div className="mb-3 flex h-[430px] w-[340px] flex-col overflow-hidden rounded-lg border bg-white shadow-2xl">
          <div className="flex items-center justify-between bg-slate-950 px-4 py-3 text-white">
            <div className="flex items-center gap-2 font-semibold"><Bot className="size-5" /> Ayuda SmartClaim</div>
            <button onClick={() => setOpen(false)} aria-label="Cerrar chat"><X className="size-5" /></button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((item, index) => (
              <div key={index} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <p className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${item.role === 'user' ? 'bg-orange-500 text-white' : 'bg-gray-100'}`}>
                  {item.text}
                </p>
              </div>
            ))}
          </div>
          <div className="flex gap-2 border-t p-3">
            <Input value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} placeholder="Escribe tu consulta..." />
            <Button size="sm" disabled={working} onClick={send} aria-label="Enviar"><Send className="size-4" /></Button>
          </div>
        </div>
      )}
      <Button onClick={() => setOpen((value) => !value)} className="size-12 rounded-full shadow-xl" aria-label="Abrir ayuda">
        <Bot className="size-5" />
      </Button>
    </div>
  );
}
