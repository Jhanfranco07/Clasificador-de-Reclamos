import type { Page } from '@playwright/test';
import { test, expect, API, headers, login } from './offline-fixture';

async function signIn(page: Page, email = 'admin@smartclaim.com') {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

async function staffHeaders(page: Page) {
  const response = await page.request.post(`${API}/api/auth/login`, { data: { email: 'admin@smartclaim.com', password: '123456' } });
  expect(response.status()).toBe(200);
  return { Authorization: `Bearer ${(await response.json()).token}` };
}

async function newCase(page: Page) {
  const owner = await headers(page);
  const orders = await (await page.request.get(`${API}/api/orders`, { headers: owner })).json();
  const created = await page.request.post(`${API}/api/claims`, { headers: owner, data: {
    customer_name: 'Jhan Perez', customer_email: 'jhan.perez@gmail.com', order_code: orders.items[0].code,
    description: 'Caso de aceptación de asignación y notificaciones', analyze: false, request_id: crypto.randomUUID(),
  } });
  expect(created.status()).toBe(201);
  return (await created.json()).claim;
}

async function send(page: Page, claimId: string, text = 'Mensaje de prueba para notificaciones') {
  const response = await page.request.post(`${API}/api/claims/${claimId}/messages`, {
    headers: await headers(page, true), data: { message: text, request_id: crypto.randomUUID() },
  });
  expect(response.status()).toBe(201);
}

test('BF-12: asignación, mis casos, escalamiento y destinatario ADMIN operables', async ({ page }) => {
  test.setTimeout(90_000);
  const claim = await newCase(page);
  const admin = await staffHeaders(page);
  const users = (await (await page.request.get(`${API}/api/claim-assignees`, { headers: admin })).json()).items;
  const agent = users.find((u: { role: string }) => u.role === 'AGENT');
  await signIn(page);
  await page.goto('/admin/claims');
  await page.getByLabel('Bandeja por responsable').selectOption('UNASSIGNED');
  await page.getByPlaceholder('Buscar código, cliente o pedido').fill(claim.code);
  await expect(page.getByRole('cell', { name: claim.code, exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Revisar', exact: true }).click();
  await page.getByLabel('Asignar responsable activo').selectOption(String(agent.id));
  await page.getByLabel('Motivo de asignación o escalamiento').fill('Atención asignada por administrador');
  await page.getByRole('button', { name: 'Confirmar asignación', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Responsable del reclamo' })).toContainText(`ID ${agent.id}`);
  await login(page, true);
  await page.goto('/admin/claims');
  await page.getByLabel('Bandeja por responsable').selectOption('MINE');
  await page.getByPlaceholder('Buscar código, cliente o pedido').fill(claim.code);
  await expect(page.getByRole('cell', { name: claim.code, exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Revisar', exact: true }).click();
  await page.getByLabel('Motivo de asignación o escalamiento').fill('Requiere revisión administrativa especializada');
  await page.getByRole('button', { name: 'Escalar con motivo' }).click();
  await expect(page.getByRole('button', { name: 'Escalar con motivo' })).toBeDisabled();
  await signIn(page);
  await page.getByRole('button', { name: 'Abrir notificaciones' }).click();
  const panel = page.getByRole('dialog', { name: 'Notificaciones', exact: true });
  await expect(panel.getByRole('heading', { name: 'Escalamiento asignado' }).first()).toBeVisible();
  await panel.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Escalamiento asignado' }) }).first().getByRole('button', { name: 'Ver reclamo', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/admin/claims/${claim.id}$`));
  await expect(page.getByText('Requiere revisión administrativa especializada', { exact: false }).last()).toBeVisible();
});

test('AF-25: contador real pasa de 3 a 4 y leer una no marca todas', async ({ page }) => {
  const claim = await newCase(page);
  const owner = await headers(page);
  await page.request.patch(`${API}/api/notifications/read`, { headers: owner });
  for (let index = 0; index < 3; index++) await send(page, claim.id, `Aviso inicial ${index}`);
  await login(page);
  await page.goto('/dashboard');
  const bell = page.getByRole('button', { name: 'Abrir notificaciones' });
  await expect(bell).toHaveText('3');
  await send(page, claim.id, 'El cuarto aviso llega después de cargar la pantalla');
  await bell.click();
  await expect(bell).toHaveText('4');
  const panel = page.getByRole('dialog', { name: 'Notificaciones', exact: true });
  await panel.getByRole('button', { name: /^Marcar notificación / }).first().click();
  await expect(bell).toHaveText('3');
  await expect(panel.getByText('Leída', { exact: true }).first()).toBeVisible();
  await panel.getByRole('button', { name: 'Marcar todas como leídas' }).click();
  await expect(bell).toHaveText('');
  await expect(panel.getByText('0 aviso(s) sin leer')).toBeVisible();
  await page.reload();
  await expect(bell).toHaveText('');
  expect((await (await page.request.get(`${API}/api/notifications`, { headers: owner })).json()).unread).toBe(0);
});

test('BF-12: foco y eventos locales actualizan la campana sin bucle de consultas', async ({ page }) => {
  const claim = await newCase(page);
  await page.request.patch(`${API}/api/notifications/read`, { headers: await headers(page) });
  await login(page);
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  await send(page, claim.id);
  let requests = 0;
  await page.route('**/api/notifications', async route => {
    requests++;
    await new Promise(resolve => setTimeout(resolve, 200));
    await route.continue();
  });
  await page.evaluate(() => {
    for (let index = 0; index < 20; index++) window.dispatchEvent(new Event('smartclaim:notifications-changed'));
    window.dispatchEvent(new Event('focus'));
  });
  await expect(page.getByRole('button', { name: 'Abrir notificaciones' })).toHaveText('1');
  expect(requests).toBe(1);
});

test('BF-12: campana distingue carga, error, reintento y fallo al marcar', async ({ page }) => {
  const claim = await newCase(page);
  await send(page, claim.id);
  await page.route('**/api/notifications', route => route.fulfill({ status: 503, json: { detail: 'Notificaciones no disponibles en prueba' } }));
  await login(page);
  await page.getByRole('button', { name: 'Abrir notificaciones' }).click();
  const panel = page.getByRole('dialog', { name: 'Notificaciones', exact: true });
  await expect(panel.getByRole('alert')).toContainText('Notificaciones no disponibles en prueba');
  await expect(panel.getByText('No tienes notificaciones.')).toHaveCount(0);
  await page.unroute('**/api/notifications');
  await panel.getByRole('button', { name: 'Reintentar notificaciones' }).click();
  await expect(panel.getByRole('article').first()).toBeVisible();
  await page.route('**/api/notifications/*/read', route => route.fulfill({ status: 503, json: { detail: 'Lectura no confirmada' } }));
  await panel.getByRole('button', { name: /^Marcar notificación / }).first().click();
  await expect(panel.getByRole('alert')).toContainText('Lectura no confirmada');
  await expect(panel.getByRole('button', { name: /^Marcar notificación / }).first()).toBeVisible();
});

test('BF-12: una cuenta nueva tiene estado vacío explícito', async ({ page }) => {
  const email = `notification-${crypto.randomUUID()}@example.com`;
  expect((await page.request.post(`${API}/api/auth/register`, { data: { name: 'Cliente nuevo', email, password: '123456' } })).status()).toBe(201);
  await signIn(page, email);
  await page.getByRole('button', { name: 'Abrir notificaciones' }).click();
  await expect(page.getByRole('dialog', { name: 'Notificaciones', exact: true }).getByText('No tienes notificaciones.')).toBeVisible();
});

for (const width of [320, 360]) {
  test(`BF-12: campana y responsable conservan acciones a ${width}px`, async ({ page }) => {
    const claim = await newCase(page);
    await page.setViewportSize({ width, height: 900 });
    await signIn(page);
    await page.goto(`/admin/claims/${claim.id}`);
    await expect(page.getByRole('region', { name: 'Responsable del reclamo' })).toBeVisible();
    await page.getByRole('button', { name: 'Abrir notificaciones' }).click();
    await expect(page.getByRole('dialog', { name: 'Notificaciones', exact: true }).getByRole('button', { name: 'Marcar todas como leídas' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  });
}
