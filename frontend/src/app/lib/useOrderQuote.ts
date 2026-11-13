import { useEffect, useState } from 'react';
import { OrderQuote, quoteOrder } from './api';

export function useOrderQuote(cart: Array<{ id: string; quantity: number }>) {
  const [result, setResult] = useState<{ key: string; quote: OrderQuote } | null>(null);
  const [error, setError] = useState('');
  const key = JSON.stringify(cart.map((item) => ({ product_id: Number(item.id), quantity: item.quantity })));
  useEffect(() => {
    let active = true;
    setResult(null);
    setError('');
    const requested = JSON.parse(key);
    if (requested.length) {
      quoteOrder(requested).then((quote) => { if (active) setResult({ key, quote }); })
        .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'No se pudo cotizar el carrito.'); });
    }
    return () => { active = false; };
  }, [key]);
  return { quote: result?.key === key ? result.quote : null, error };
}
