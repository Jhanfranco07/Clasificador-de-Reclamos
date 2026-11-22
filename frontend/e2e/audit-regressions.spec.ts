// These expectations deliberately expose tickets outside Phase 1; no test.skip/fixme.
import { test, expect, API, headers, login, claim } from './offline-fixture';

test('AF-03 corregido: borrador no aparece antes de publicar', async ({ page }) => {
  const detail = await claim(page);
  await page.request.patch(`${API}/api/responses/${detail.response.id}`, { headers: await headers(page, true), data: { response_text: 'AUDIT-PRIVATE-DRAFT' } });
  await login(page);
  await page.goto(`/claims/${detail.claim.id}`);
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.getByText('AUDIT-PRIVATE-DRAFT', { exact: true })).toHaveCount(0);
});

test('AF-27 corregido por retiro: ayuda sin búsqueda o contactos ficticios', async ({ page }) => {
  await login(page);
  await page.goto('/help');
  await expect(page.getByRole('heading', { name: 'Centro de Ayuda', exact: true })).toBeVisible();
  await expect(page.getByPlaceholder('Busca una pregunta o tema...')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Correo no disponible' })).toBeDisabled();
});

test('AF-28 corregido BF-14: configuración persiste al recargar', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('admin@smartclaim.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto('/admin/ai-config');
  const toggle = page.getByRole('switch').first();
  await expect(toggle).toHaveAttribute('aria-checked', 'true');
  await toggle.click();
  await page.getByRole('button', { name: 'Guardar configuración', exact: true }).click();
  await expect(page.getByText(/Configuración guardada/)).toBeVisible();
  const loaded = page.waitForResponse((r) => r.url().endsWith('/api/config'));
  await page.reload();
  await loaded;
  await expect(page.getByRole('switch').first()).toHaveAttribute('aria-checked', 'false');
});

test('AF-12 corregido: catálogo vacío no aparenta restaurantes', async ({ page }) => {
  await page.route('**/api/catalog', (r) => r.fulfill({ json: { items: [] } }));
  await page.goto('/');
  await expect(page.getByText('No hay restaurantes disponibles.', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver restaurante', exact: true })).toHaveCount(0);
});

test('AF-13 corregido BF-16: detalle público anunciado por catálogo', async ({ page }) => {
  const catalog = await (await page.request.get(`${API}/api/catalog`)).json();
  await page.goto('/');
  await page.getByRole('link', { name: 'Ver restaurante', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: catalog.items[0].name, exact: true, level: 1 })).toBeVisible();
  await expect(page).toHaveURL(/\/restaurants\/\d+$/);
});

test('AF-16 corregido BF-16: carrito corrupto no deja pantalla vacía', async ({ page }) => {
  await login(page);
  await page.evaluate(() => localStorage.setItem('smartclaim_pending_cart', '{invalid-json'));
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/cart');
  await page.waitForLoadState('networkidle');
  expect(errors).toEqual([]);
  await expect(page.locator('h1')).toBeVisible();
});

test('AF-25 corregido BF-12: campana refleja respuestas nuevas', async ({ page }) => {
  const detail = await claim(page);
  await login(page);
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  await page.request.post(`${API}/api/claims/${detail.claim.id}/messages`, { headers: await headers(page, true), data: { message: 'Audit new reply' } });
  await page.getByRole('button', { name: 'Abrir notificaciones' }).click();
  const actual = await (await page.request.get(`${API}/api/notifications`, { headers: await headers(page) })).json();
  expect(Number((await page.getByRole('button', { name: 'Abrir notificaciones' }).innerText()).trim() || 0)).toBe(actual.unread);
});
