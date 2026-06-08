import { useEffect, useRef, useState } from 'react';
import { Bot, Send, X } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { sendChatMessage } from '../lib/api';
import TypingIndicator from './TypingIndicator';
import { useAuth } from '../contexts/AuthContext';

const CART_KEY = 'smartclaim_pending_cart';

const greetingFor = (name?: string) => (
  name
    ? `Hola ${name.split(' ')[0]}. Puedo orientarte sobre pedidos, pagos y reclamos.`
    : 'Hola. Puedo orientarte sobre pedidos, pagos y reclamos.'
);

const createSessionId = (identity: string) => `chat_session_${identity}_${Date.now()}`;

export default function ChatbotWidget() {
  const { currentUser } = useAuth();
  const identity = currentUser?.id || 'visitor';
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'bot'; text: string }>>([
    { role: 'bot', text: greetingFor(currentUser?.name) },
  ]);
  const [working, setWorking] = useState(false);
  const [sessionId, setSessionId] = useState(() => createSessionId(identity));
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const currentIdentityRef = useRef(identity);
  const requestGenerationRef = useRef(0);

  useEffect(() => {
    if (currentIdentityRef.current === identity) return;

    currentIdentityRef.current = identity;
    requestGenerationRef.current += 1;
    setOpen(false);
    setText('');
    setWorking(false);
    setSessionId(createSessionId(identity));
    setMessages([{ role: 'bot', text: greetingFor(currentUser?.name) }]);
  }, [currentUser?.name, identity]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, working]);

  const send = async () => {
    if (text.trim().length < 2 || working) return;
    const value = text.trim();
    const requestIdentity = currentIdentityRef.current;
    const requestGeneration = requestGenerationRef.current;
    const requestIsCurrent = () => (
      currentIdentityRef.current === requestIdentity
      && requestGenerationRef.current === requestGeneration
    );

    setText('');
    setMessages((items) => [...items, { role: 'user', text: value }]);
    setWorking(true);

    try {
      let cart: Array<{ quantity?: number; price?: number }> = [];
      try {
        cart = JSON.parse(window.localStorage.getItem(CART_KEY) || '[]');
      } catch {
        cart = [];
      }
      const result = await sendChatMessage(value, sessionId, {
        cart: {
          quantity: cart.reduce((total, item) => total + Number(item.quantity || 0), 0),
          subtotal: cart.reduce((total, item) => total + Number(item.quantity || 0) * Number(item.price || 0), 0),
        },
      });
      if (!requestIsCurrent()) return;
      setMessages((items) => [...items, { role: 'bot', text: result.message }]);
    } catch {
      if (!requestIsCurrent()) return;
      setMessages((items) => [
        ...items,
        { role: 'bot', text: 'No pude procesar tu consulta en este momento. Inténtalo nuevamente.' },
      ]);
    } finally {
      if (requestIsCurrent()) setWorking(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-[120]">
      {open && (
        <div className="mb-3 flex h-[430px] w-[340px] flex-col overflow-hidden rounded-lg border bg-white shadow-2xl">
          <div className="flex items-center justify-between bg-slate-950 px-4 py-3 text-white">
            <div>
              <div className="flex items-center gap-2 font-semibold">
                <Bot className="size-5" /> Asistente SmartClaim AI
              </div>
              <p className="mt-0.5 text-[11px] text-white/70">Pedidos, pagos y reclamos</p>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Cerrar chat">
              <X className="size-5" />
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((item, index) => (
              <div key={index} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <p className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${item.role === 'user' ? 'bg-orange-500 text-white' : 'bg-gray-100'}`}>
                  {item.text}
                </p>
              </div>
            ))}
            {working && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
          <div className="flex gap-2 border-t p-3">
            <Input
              disabled={working}
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && send()}
              placeholder={working ? 'Espera la respuesta...' : 'Escribe tu consulta...'}
            />
            <Button size="sm" disabled={working} onClick={send} aria-label="Enviar">
              <Send className="size-4" />
            </Button>
          </div>
        </div>
      )}
      <Button
        onClick={() => setOpen((value) => !value)}
        className="size-12 rounded-full shadow-xl"
        aria-label="Abrir ayuda"
      >
        <Bot className="size-5" />
      </Button>
    </div>
  );
}
