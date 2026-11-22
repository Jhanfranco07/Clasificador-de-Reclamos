import type { Page } from '@playwright/test';
import { test, expect, API, login } from './offline-fixture';

async function signIn(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

async function setup(page: Page) {
  const adminResponse = await page.request.post(`${API}/api/auth/login`, { data: { email: 'admin@smartclaim.com', password: '123456' } });
  expect(adminResponse.status()).toBe(200);
  const admin = { Authorization: `Bearer ${(await adminResponse.json()).token}` };
  const accounts: Record<string, { id: number; email: string; token: string }> = {};
  for (const role of ['MERCHANT', 'COURIER']) {
    const email = `${role.toLowerCase()}-${crypto.randomUUID()}@example.com`;
    const created = await page.request.post(`${API}/api/auth/register`, { data: { name: `Test ${role}`, email, password: '123456' } });
    expect(created.status()).toBe(201);
    const account = await created.json();
    expect((await page.request.patch(`${API}/api/operations/users/${account.user.id}`, { headers: admin, data: {
      role, active: true, reason: 'Aceptación navegador', request_id: crypto.randomUUID(),
    } })).status()).toBe(200);
    accounts[role] = { id: Number(account.user.id), email, token: account.token };
  }
  expect((await page.request.put(`${API}/api/operations/restaurants/1/operator`, { headers: admin, data: {
    user_id: accounts.MERCHANT.id, active: true, edit_products: false, reason: 'Autorización de prueba', request_id: crypto.randomUUID(),
  } })).status()).toBe(200);
  return { admin, accounts };
}

test('Fase 2B: compra, comercio, asignación, entrega, historial y atención por agente desde UI', async ({ page }) => {
  test.setTimeout(90_000);
  const { accounts } = await setup(page);
  await login(page);
  await page.goto('/restaurants/1');
  await page.getByRole('button', { name: /^Agregar / }).first().click();
  await page.goto('/checkout');
  const created = page.waitForResponse(r => r.url().endsWith('/api/orders') && r.request().method() === 'POST');
  await expect(page.getByRole('button', { name: 'Confirmar pedido', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Confirmar pedido', exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const order = (await response.json()).order;
  expect(order.status).toBe('RECEIVED');

  await signIn(page, accounts.MERCHANT.email);
  await expect(page).toHaveURL(/\/merchant$/);
  await page.goto(`/merchant/orders/${order.id}`);
  for (const label of ['Aceptado', 'Preparando', 'Listo para recoger']) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.getByText('Estado actual ·')).toContainText(label);
  }
  expect((await page.request.get(`${API}/api/config`, { headers: { Authorization: `Bearer ${accounts.MERCHANT.token}` } })).status()).toBe(403);

  expect((await page.request.put(`${API}/api/operations/availability`, { headers: { Authorization: `Bearer ${accounts.COURIER.token}` }, data: { available: true, request_id: crypto.randomUUID() } })).status()).toBe(200);
  await signIn(page, 'admin@smartclaim.com');
  await page.goto(`/admin/orders/${order.id}`);
  await page.getByLabel('Motivo de intervención o rechazo').fill('Asignación controlada en prueba');
  await page.getByLabel('Repartidor disponible').selectOption(String(accounts.COURIER.id));
  await page.getByRole('button', { name: 'Asignar repartidor', exact: true }).click();
  await expect(page.getByText(`Repartidor ID ${accounts.COURIER.id}`)).toBeVisible();

  await signIn(page, accounts.COURIER.email);
  await expect(page).toHaveURL(/\/courier$/);
  await page.goto(`/courier/orders/${order.id}`);
  await page.getByRole('button', { name: 'Confirmar recogida y salida', exact: true }).click();
  await expect(page.getByText('Estado actual ·')).toContainText('En camino');
  await page.getByRole('button', { name: 'Confirmar entrega', exact: true }).click();
  await expect(page.getByText('Estado actual ·')).toContainText('Entregado');
  await expect(page.getByRole('button', { name: 'Confirmar entrega', exact: true })).toHaveCount(0);

  await login(page);
  await page.goto(`/orders/${order.id}`);
  await expect(page.getByRole('region', { name: 'Historial del pedido' })).toContainText('Entregado');
  await page.getByRole('button', { name: 'Crear reclamo', exact: true }).click();
  await page.getByLabel('Descripción del problema *').fill('El producto recibido era distinto del producto solicitado');
  const claimResult = page.waitForResponse(r => r.url().endsWith('/api/claims') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Enviar reclamo', exact: true }).click();
  const claimResponse = await claimResult;
  expect(claimResponse.status()).toBe(201);
  const claim = (await claimResponse.json()).claim;
  await login(page, true);
  await page.goto(`/admin/claims/${claim.id}`);
  await expect(page.getByRole('region', { name: 'Contexto verificado del pedido' })).toContainText(order.code);
  await expect(page.getByRole('region', { name: 'Contexto verificado del pedido' })).toContainText('Entregado');
  await page.getByRole('button', { name: 'Enviar respuesta al cliente', exact: true }).click();
  await expect(page.getByText('Respuesta enviada al cliente correctamente.', { exact: true }).first()).toBeVisible();
});

test('Fase 2B: carrito mixto exige confirmación y conserva artículos del otro comercio', async ({ page }) => {
  await login(page);
  const catalog = (await (await page.request.get(`${API}/api/catalog`)).json()).items;
  const stores = catalog.filter((r: { products: unknown[] }) => r.products.length).slice(0, 2);
  const cart = stores.map((r: { name: string; products: Array<{ id: string; name: string; price: number }> }) => ({
    id: r.products[0].id, name: r.products[0].name, price: r.products[0].price,
    restaurantName: r.name, image: '', quantity: 1,
  }));
  await page.evaluate(items => localStorage.setItem('smartclaim_pending_cart', JSON.stringify(items)), cart);
  await page.goto('/cart');
  await expect(page.getByRole('button', { name: 'Continuar al pago', exact: true })).toBeDisabled();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', { name: `Comprar por separado · ${stores[0].name}`, exact: true }).click();
  await expect(page).toHaveURL(/\/cart$/);
  page.once('dialog', dialog => dialog.accept());
  await page.route('**/api/orders/quote', route => route.fulfill({ status: 503, json: { detail: 'Cotización separada no disponible' } }));
  await page.getByRole('button', { name: `Comprar por separado · ${stores[0].name}`, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`checkout\\?restaurant=${stores[0].id}$`));
  await expect(page.getByRole('alert')).toContainText('Cotización separada no disponible');
  await expect(page.getByText('Tu carrito está vacío', { exact: true })).toHaveCount(0);
  await page.unroute('**/api/orders/quote');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Confirmar pedido', exact: true })).toBeEnabled();
  const created = page.waitForResponse(r => r.url().endsWith('/api/orders') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar pedido', exact: true }).click();
  expect((await created).status()).toBe(201);
  await expect(page).toHaveURL(/\/orders\/\d+$/);
  const remaining = await page.evaluate(() => JSON.parse(localStorage.getItem('smartclaim_pending_cart') || '[]'));
  expect(remaining).toHaveLength(1);
  expect(remaining[0].id).toBe(cart[1].id);
});

for (const width of [320, 360, 1280]) {
  test(`Fase 2B: portales de comercio, repartidor y administrador responsive ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const { accounts } = await setup(page);
    for (const [email, path, heading] of [
      [accounts.MERCHANT.email, '/merchant', 'Gestión de pedidos'],
      [accounts.COURIER.email, '/courier', 'Entregas asignadas'],
      ['admin@smartclaim.com', '/admin/operations', 'Comercios, roles y operadores'],
    ]) {
      await signIn(page, email);
      await page.goto(path);
      await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
      await expect(page.getByText(/Cargando (operación|administración)/)).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: `test-results/offline/phase2b-${path.split('/').pop()}-${width}.png` });
    }
  });
}

test('Fase 2B: ADMIN concede y revoca una autorización desde interfaz', async ({ page }) => {
  const { accounts } = await setup(page);
  await signIn(page, 'admin@smartclaim.com');
  await page.goto('/admin/operations');
  await page.getByLabel('Establecimiento', { exact: true }).selectOption('1');
  await page.getByLabel('Operador MERCHANT', { exact: true }).selectOption(String(accounts.MERCHANT.id));
  await page.getByLabel('Permitir editar productos').check();
  await page.getByLabel('Motivo de autorización').fill('Permiso verificado en navegador');
  const saved = page.waitForResponse(r => r.url().endsWith('/operator') && r.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Guardar autorización' }).click();
  expect((await saved).status()).toBe(200);
  await expect(page.getByRole('button', { name: 'Guardar autorización' })).toBeEnabled();
  await page.getByLabel('Autorización activa').uncheck();
  const revoked = page.waitForResponse(r => r.url().endsWith('/operator') && r.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Guardar autorización' }).click();
  expect((await revoked).status()).toBe(200);
  expect((await page.request.get(`${API}/api/orders`, { headers: { Authorization: `Bearer ${accounts.MERCHANT.token}` } })).status()).toBe(200);
});

test('Fase 2B: portales aíslan navegación y distinguen error de listado vacío', async ({ page }) => {
  const { accounts } = await setup(page);
  for (const [role, home] of [['MERCHANT', '/merchant'], ['COURIER', '/courier']]) {
    await signIn(page, accounts[role].email);
    await page.goto('/admin/operations');
    await expect(page).toHaveURL(home);
    await page.goto('/orders');
    await expect(page).toHaveURL(home);
  }
  await page.route('**/api/orders', route => route.fulfill({ status: 503, json: { detail: 'Operación no disponible en prueba' } }));
  await page.goto('/courier');
  await expect(page.getByRole('alert')).toContainText('Operación no disponible en prueba');
  await expect(page.getByText('No hay pedidos autorizados para esta cuenta.')).toHaveCount(0);
});
