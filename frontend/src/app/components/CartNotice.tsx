import { Button } from './ui/button';

export default function CartNotice({ warning, reset }: { warning: string; reset: () => unknown }) {
  if (!warning) return null;
  return <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-950 space-y-2">
    <p>{warning}</p><Button variant="outline" onClick={reset}>Restablecer carrito</Button>
  </div>;
}
