import { FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { UserRound } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import ClientLayout from '../components/ClientLayout';
import AdminLayout from '../components/AdminLayout';

export default function ProfilePage() {
  const { currentUser, updateProfile } = useAuth();
  const [name, setName] = useState(currentUser?.name || '');
  const [phone, setPhone] = useState(currentUser?.phone || '');
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await updateProfile({ name, phone });
      toast.success('Perfil actualizado correctamente');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo actualizar el perfil');
    } finally {
      setSaving(false);
    }
  };

  const content = (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="size-5" />Mi perfil</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-5">
            <div className="space-y-2"><Label htmlFor="profile-name">Nombre</Label><Input id="profile-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} required /></div>
            <div className="space-y-2"><Label htmlFor="profile-email">Correo</Label><Input id="profile-email" value={currentUser?.email || ''} disabled /><p className="text-xs text-gray-500">El correo identifica tu cuenta y no se puede modificar desde el perfil.</p></div>
            <div className="space-y-2"><Label htmlFor="profile-phone">Teléfono</Label><Input id="profile-phone" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="Ej. 999 999 999" /></div>
            <Button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Guardar cambios'}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
  return currentUser?.role === 'CLIENT' ? <ClientLayout>{content}</ClientLayout> : <AdminLayout>{content}</AdminLayout>;
}
