import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { Bot, Minus, Send, ShoppingCart, X } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { getCatalog, sendChatMessage, type ChatRecommendation } from '../lib/api';
import { CART_KEY, parseCart, readCart } from '../lib/cart';
import TypingIndicator from './TypingIndicator';
import { useAuth } from '../contexts/AuthContext';

const DISMISSED_KEY = 'smartclaim_chat_dismissed';
const AUTO_SHOWN_KEY = 'smartclaim_chat_auto_shown';
const alreadyShown = () => {
  try { return window.sessionStorage.getItem(AUTO_SHOWN_KEY) === '1'; }
  catch { return false; }
};
const dismissed = () => {
  try { return window.sessionStorage.getItem(DISMISSED_KEY) === '1'; }
  catch { return false; }
};
const greetingFor = (name?: string) => name
  ? `Hola ${name.split(' ')[0]}. Soy tu asistente de compras y atención. ¿Qué te gustaría hacer?`
  : '¡Hola! Soy tu asistente de compras y atención. ¿Qué te gustaría hacer?';
const quickActions = [
  { label: 'Recomendar platos', message: 'Recomiéndame platos' },
  { label: 'Realizar pedido', message: '¿Cómo hago un pedido?' },
  { label: 'Consultar pedidos', message: 'Muéstrame mis pedidos recientes' },
  { label: 'Solicitar ayuda', message: 'Necesito contactar soporte' },
];
type ChatMessage = { role: 'user' | 'bot'; text: string; recommendations?: ChatRecommendation[] };

export default function ChatbotWidget() {
  const { pathname } = useLocation();
  const { currentUser } = useAuth();
  const shoppingPage = !/^\/(admin|merchant|courier)(\/|$)/.test(pathname);
  // El asistente está disponible desde el primer acceso del cliente,
  // incluso si navega a la portada pública mientras conserva la sesión.
  const isClient = currentUser?.role === 'CLIENT';
  const visible = Boolean(currentUser) && (pathname !== '/' || isClient) &&
    !/^\/(login|register|registro|recuperar|password-reset|forgot-password|auth)(\/|$)/.test(pathname);
  const identity = currentUser?.id || 'visitor';
  // La bienvenida se abre en el panel de entrada, no encima de flujos operativos.
  const introPage = isClient
    ? /^\/(dashboard|restaurants|products)\/?$/.test(pathname)
    : /^\/(admin|merchant|courier)\/?$/.test(pathname);
  const [open, setOpen] = useState(() => !dismissed() && !alreadyShown() && introPage);
  const [text, setText] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: 'bot', text: greetingFor(currentUser?.name) }]);
  const [working, setWorking] = useState(false);
  const [sessionId, setSessionId] = useState(() => `chat_session_${identity}_${Date.now()}`);
  const [pendingProduct, setPendingProduct] = useState<string | null>(null);
  const [cartNotice, setCartNotice] = useState('');
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const identityRef = useRef(identity);
  const generationRef = useRef(0);
  const previousPathRef = useRef(pathname);
  const chatNavigationRef = useRef(false);

  useEffect(() => {
    if (identityRef.current === identity) return;
    identityRef.current = identity;
    generationRef.current += 1;
    if (identity === 'visitor') {
      try { window.sessionStorage.removeItem(AUTO_SHOWN_KEY); } catch { /* Optional storage. */ }
      setOpen(false);
    } else {
      setOpen((wasOpen) => wasOpen || (!dismissed() && !alreadyShown() && introPage));
    }
    setText(''); setWorking(false); setPendingProduct(null); setCartNotice('');
    setSessionId(`chat_session_${identity}_${Date.now()}`);
    setMessages([{ role: 'bot', text: greetingFor(currentUser?.name) }]);
  }, [currentUser?.name, identity, introPage]);

  useEffect(() => {
    if (!visible || !introPage || alreadyShown()) return;
    try { window.sessionStorage.setItem(AUTO_SHOWN_KEY, '1'); } catch { /* Optional storage. */ }
    if (!dismissed()) setOpen(true);
  }, [visible, introPage]);

  useEffect(() => {
    const previous = previousPathRef.current;
    previousPathRef.current = pathname;
    if (previous === pathname) return;
    const fromAuth = /^\/(login|register|registro|auth)(\/|$)/.test(previous);
    if (!fromAuth && !chatNavigationRef.current) setOpen(false);
    chatNavigationRef.current = false;
  }, [pathname]);

  useEffect(() => {
    if (!open || !visible) return;
    const closeOnOutsideInteraction = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Element && !target.closest('[aria-label="Asistente SmartClaim AI"], [aria-label="Abrir ayuda"], [aria-label="Minimizar ayuda"]')) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', closeOnOutsideInteraction);
    return () => document.removeEventListener('pointerdown', closeOnOutsideInteraction);
  }, [open, visible]);

  useEffect(() => {
    if (open) {
      const viewport = messagesRef.current;
      viewport?.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, working, open]);

  const close = () => {
    try { window.sessionStorage.setItem(DISMISSED_KEY, '1'); } catch { /* Storage can be unavailable. */ }
    setOpen(false);
  };

  const send = async (message: string) => {
    const value = message.trim();
    if (value.length < 2 || working) return;
    const requestIdentity = identityRef.current;
    const requestGeneration = generationRef.current;
    const isCurrent = () => identityRef.current === requestIdentity && generationRef.current === requestGeneration;
    const history = messages.slice(-8).map(({ role, text: content }) => ({ role, text: content }));
    setText(''); setCartNotice('');
    setMessages((items) => [...items, { role: 'user', text: value }]);
    setWorking(true);
    try {
      const cart = readCart();
      const result = await sendChatMessage(value, sessionId, {
        history,
        cart: {
          quantity: cart.items.reduce((total, item) => total + item.quantity, 0),
          subtotal: cart.items.reduce((total, item) => total + item.quantity * item.price, 0),
        },
      });
      if (isCurrent()) setMessages((items) => [...items, {
        role: 'bot', text: result.message, recommendations: result.recommendations,
      }]);
    } catch {
      if (isCurrent()) setMessages((items) => [...items, { role: 'bot', text: 'No pude procesar tu consulta. Inténtalo nuevamente.' }]);
    } finally {
      if (isCurrent()) setWorking(false);
    }
  };

  const addRecommended = async (recommendation: ChatRecommendation) => {
    try {
      const { items } = await getCatalog();
      const restaurant = items.find((item) => item.id === recommendation.restaurantId);
      const product = restaurant?.products.find((item) => item.id === recommendation.productId);
      if (!restaurant || !product) {
        setCartNotice('Ese producto ya no está disponible. Pide una recomendación nueva.');
        setPendingProduct(null);
        return;
      }
      const snapshot = readCart();
      if (snapshot.blocked) { setCartNotice(snapshot.warning); return; }
      const existing = snapshot.items.find((item) => item.id === product.id);
      const next = existing
        ? snapshot.items.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
        : [...snapshot.items, { ...product, image: product.image || '', quantity: 1,
            restaurantName: restaurant.name, restaurantImage: restaurant.image }];
      const checked = parseCart(JSON.stringify(next));
      if (checked.blocked) { setCartNotice(checked.warning); return; }
      window.localStorage.setItem(CART_KEY, JSON.stringify(checked.items));
      window.dispatchEvent(new Event('smartclaim:cart-changed'));
      setCartNotice(`${product.name} agregado al carrito.`);
      setPendingProduct(null);
    } catch {
      setCartNotice('No pude verificar el catálogo o guardar el carrito. Inténtalo nuevamente.');
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[120] sm:bottom-5 sm:right-5">
      {open && <section aria-label="Asistente SmartClaim AI" className="pointer-events-auto fixed inset-x-3 bottom-20 flex h-[min(70dvh,620px)] max-h-[calc(100dvh-6rem)] flex-col overflow-hidden rounded-2xl border border-border bg-card text-card-foreground shadow-2xl shadow-slate-950/30 sm:inset-x-auto sm:right-5 sm:w-[390px]">
        <header className="flex shrink-0 items-center justify-between bg-slate-900 px-4 py-3 text-white">
          <div><div className="flex items-center gap-2 font-semibold"><Bot className="size-5" /> Asistente SmartClaim AI</div><p className="mt-0.5 text-xs text-white/75">Compras y atención, con opciones reales</p></div>
          <div className="flex">
            <button type="button" onClick={close} aria-label="Minimizar chat" className="pointer-events-auto rounded-lg p-2 hover:bg-white/15 focus-visible:outline focus-visible:outline-2"><Minus className="size-5" /></button>
            <button type="button" onClick={close} aria-label="Cerrar chat" className="pointer-events-auto rounded-lg p-2 hover:bg-white/15 focus-visible:outline focus-visible:outline-2"><X className="size-5" /></button>
          </div>
        </header>
        <div ref={messagesRef} role="log" aria-label="Conversación" aria-live="polite" className="min-h-0 flex-1 touch-pan-y space-y-3 overflow-y-auto overscroll-contain p-3">
          {messages.map((item, index) => <div key={index} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm ${item.role === 'user' ? 'bg-orange-500 text-white' : 'bg-muted text-foreground'}`}>
              <p className="whitespace-pre-wrap">{item.text}</p>
              {item.recommendations?.map((product) => <div key={product.productId} className="mt-2 min-w-0 rounded-xl border border-border bg-card p-2 text-card-foreground">
                <div className="flex min-w-0 gap-2">
                  {product.image && <img src={product.image} alt="" loading="lazy" className="size-14 shrink-0 rounded-lg object-cover" />}
                  <div className="min-w-0"><p className="break-words font-semibold">{product.name}</p>
                    <p className="text-xs text-muted-foreground">{product.restaurant} · {product.category}</p>
                    <p className="font-semibold text-orange-700 dark:text-orange-300">S/ {product.price.toFixed(2)}</p></div>
                </div>
                {product.description && <p className="mt-1 break-words text-xs">{product.description}</p>}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="outline" asChild><Link className="pointer-events-auto" onClick={() => { chatNavigationRef.current = true; }} to={`/restaurants/${product.restaurantId}#product-${product.productId}`}>Ver producto</Link></Button>
                  {pendingProduct === product.productId
                    ? <><Button type="button" size="sm" className="pointer-events-auto" onClick={() => void addRecommended(product)}>Confirmar</Button><Button type="button" size="sm" variant="ghost" className="pointer-events-auto" onClick={() => setPendingProduct(null)}>Cancelar</Button></>
                    : <Button type="button" size="sm" className="pointer-events-auto" onClick={() => setPendingProduct(product.productId)}><ShoppingCart className="mr-1 size-4" />Agregar</Button>}
                </div>
              </div>)}
            </div>
          </div>)}
          {working && <TypingIndicator />}
        </div>
        <div className="shrink-0 border-t border-border bg-card px-3 py-2">
          {shoppingPage && <div className="grid grid-cols-2 gap-2" aria-label="Opciones rápidas">
            {quickActions.map((action) => <Button key={action.label} type="button" size="sm" variant="outline" disabled={working} className="pointer-events-auto h-auto min-h-10 min-w-0 whitespace-normal rounded-xl px-2 py-1.5 text-center leading-tight" onClick={() => void send(action.message)}>{action.label}</Button>)}
          </div>}
          {cartNotice && <p role="status" className="py-1 text-xs">{cartNotice}</p>}
          <form className="mt-2 flex gap-2" onSubmit={(event) => { event.preventDefault(); void send(text); }}>
            <label htmlFor="smartclaim-chat-input" className="sr-only">Escribe tu mensaje</label>
            <Input id="smartclaim-chat-input" name="message" className="pointer-events-auto" value={text} onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Enter' && event.nativeEvent.isComposing) event.preventDefault(); }}
              maxLength={2000} disabled={working} placeholder={working ? 'Preparando respuesta...' : 'Escribe tu consulta...'} />
            <Button type="submit" size="sm" className="pointer-events-auto" disabled={working || text.trim().length < 2} aria-label="Enviar mensaje"><Send className="size-4" /></Button>
          </form>
        </div>
      </section>}
      <Button type="button" onClick={() => open ? close() : setOpen(true)} aria-label={open ? 'Minimizar ayuda' : 'Abrir ayuda'} aria-expanded={open}
        className="flex h-12 min-w-12 items-center justify-center gap-2 rounded-full border border-orange-300/30 bg-orange-600 px-3 text-white shadow-xl shadow-orange-950/30 hover:bg-orange-500 focus-visible:ring-2 focus-visible:ring-orange-300 sm:px-4"><Bot className="size-5 shrink-0" aria-hidden="true" /><span className="hidden text-sm font-semibold sm:inline">Asistente IA</span></Button>
    </div>
  );
}
