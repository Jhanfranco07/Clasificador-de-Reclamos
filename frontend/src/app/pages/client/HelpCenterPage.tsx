import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import ClientLayout from '../../components/ClientLayout';

export default function HelpCenterPage() {
  return (
    <ClientLayout>
      <div className="mx-auto max-w-4xl space-y-6">
        <h1 className="text-3xl font-bold">Centro de Ayuda</h1>
        <Card><CardHeader><CardTitle>Alcance de la demostración</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p>SmartClaim AI es un proyecto académico. Los pedidos se guardan, pero no se procesan ni verifican pagos bancarios.</p>
            <p>No hay seguimiento GPS, integración con repartidores ni devoluciones automáticas. Un estado de pedido o un cierre de reclamo no acredita una transacción financiera.</p>
            <p>No se envían correos automáticos de seguimiento. Consulta las respuestas y notificaciones dentro de la aplicación.</p>
          </CardContent>
        </Card>
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardHeader><CardTitle>Pedidos e incidentes</CardTitle></CardHeader><CardContent className="space-y-3">
            <p>Revisa tus pedidos y describe el problema en un reclamo. El equipo puede revisar el caso y responder desde la conversación.</p>
            <Button asChild><Link to="/orders">Consultar mis pedidos</Link></Button>
            <Button asChild variant="outline"><Link to="/claims/new">Crear reclamo</Link></Button>
          </CardContent></Card>
          <Card><CardHeader><CardTitle>Consultas documentales</CardTitle></CardHeader><CardContent className="space-y-3">
            <p>Usa el botón flotante de ayuda para consultar al asistente. Busca en los documentos FAQ disponibles; si no encuentra una respuesta suficiente, no confirma una coincidencia.</p>
            <p>El asistente no sustituye la revisión humana ni confirma compensaciones. Las sugerencias de reclamos requieren publicación del agente.</p>
          </CardContent></Card>
        </div>
        <Card><CardHeader><CardTitle>Canales de atención</CardTitle></CardHeader><CardContent className="space-y-3">
          <p>La conversación de cada reclamo es el canal operativo disponible. No hay un horario o plazo de respuesta garantizado en esta demostración.</p>
          <Button asChild><Link to="/claims">Ver mis reclamos</Link></Button>
          <div className="flex flex-wrap gap-3"><Button disabled variant="outline">Correo no disponible</Button><Button disabled variant="outline">Atención telefónica no disponible</Button></div>
        </CardContent></Card>
      </div>
    </ClientLayout>
  );
}
