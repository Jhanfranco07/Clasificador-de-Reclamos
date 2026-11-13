import { test, expect, API, headers, login, claim } from './offline-fixture';

test('BF-01: borrador privado y aprobación sin duplicados', async ({ page }) => {
  const detail = await claim(page);
  await login(page, true);
  await page.goto(`/admin/claims/${detail.claim.id}`);
  await page.getByRole('button', { name: 'Editar respuesta', exact: true }).click();
  await page.locator('textarea').first().fill('PRIVATE-DRAFT-PHASE1');
  await page.getByRole('button', { name: 'Guardar edicion', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Editar respuesta', exact: true })).toBeVisible();
  await login(page);
  await page.goto(`/claims/${detail.claim.id}`);
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.getByText('PRIVATE-DRAFT-PHASE1', { exact: true })).toHaveCount(0);
  const agent = await headers(page, true);
  for (let i = 0; i < 2; i++) {
    expect((await page.request.post(`${API}/api/responses/${detail.response.id}/approve`, { headers: agent })).status()).toBe(200);
  }
  await page.reload();
  await expect(page.getByText(/PRIVATE-DRAFT-PHASE1/).first()).toBeVisible();
  const messages = await (await page.request.get(`${API}/api/claims/${detail.claim.id}/messages`, { headers: await headers(page) })).json();
  expect(messages.items.filter((item: { message: string }) => item.message.includes('PRIVATE-DRAFT-PHASE1'))).toHaveLength(1);
});

test('BF-02: rechaza pedido ajeno y conserva reclamos propios', async ({ page }) => {
  const owner = await headers(page);
  const orders = await (await page.request.get(`${API}/api/orders`, { headers: owner })).json();
  const registered = await page.request.post(`${API}/api/auth/register`, { data: {
    name: 'Isolated other client', email: `other-${Date.now()}@example.com`, password: '123456',
  } });
  const account = await registered.json();
  const r = await page.request.post(`${API}/api/claims`, { headers: { Authorization: `Bearer ${account.token}` }, data: {
    customer_name: account.user.name, customer_email: account.user.email, order_code: orders.items[0].code,
    description: 'Complaint for an order that belongs to another customer', analyze: false,
  } });
  expect(r.status()).toBe(404);
  await login(page);
  await page.goto(`/claims/new?orderId=${orders.items[0].id}`);
  await expect(page.getByRole('combobox')).toContainText(orders.items[0].code);
  await page.getByLabel('Descripción del problema *').fill('Nuevo incidente sobre mi pedido, sin restringir otros reclamos legítimos.');
  const created = page.waitForResponse((res) => res.url().endsWith('/api/claims') && res.request().method() === 'POST');
  await page.getByRole('button', { name: 'Enviar reclamo', exact: true }).click();
  expect((await created).status()).toBe(201);
  await expect(page.getByRole('heading', { name: 'Reclamo recibido' })).toBeVisible();
});

test('BF-03: compra cotizada ignora precios locales y conserva instrucciones', async ({ page }) => {
  await login(page);
  await page.goto('/restaurants/1');
  await page.getByRole('button', { name: /^Agregar / }).first().click();
  await page.evaluate(() => {
    const items = JSON.parse(localStorage.getItem('smartclaim_pending_cart') || '[]');
    for (const item of items) item.price = 0;
    localStorage.setItem('smartclaim_pending_cart', JSON.stringify(items));
  });
  await page.goto('/cart');
  await expect(page.getByRole('button', { name: 'Continuar al pago' })).toBeEnabled();
  const total = await page.getByText('Total cotizado con cargos').locator('..').innerText();
  await page.getByRole('button', { name: 'Continuar al pago' }).click();
  await page.getByLabel('Referencia de entrega').fill('PHASE1-NOTES');
  await expect(page.getByRole('button', { name: 'Confirmar pedido', exact: true })).toBeEnabled();
  const result = page.waitForResponse((r) => r.url().endsWith('/api/orders') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar pedido', exact: true }).click();
  const response = await result;
  expect(response.status()).toBe(201);
  const order = (await response.json()).order;
  expect(order.total).toBeGreaterThan(0);
  expect(order.deliveryNotes).toBe('PHASE1-NOTES');
  expect(response.request().postDataJSON().items[0].price).toBeUndefined();
  expect(total).toContain(order.total.toFixed(2));
  await expect(page).toHaveURL(new RegExp(`/orders/${order.id}$`));
});

test('BF-04: catálogo vacío y error no muestran comercios ficticios', async ({ page }) => {
  await page.goto('/');
  const catalog = await (await page.request.get(`${API}/api/catalog`)).json();
  expect(catalog.items.length).toBeGreaterThan(0);
  await expect(page.getByRole('link', { name: 'Ver restaurante', exact: true })).toHaveCount(catalog.items.length);
  await page.route('**/api/catalog', (route) => route.fulfill({ json: { items: [] } }));
  await page.goto('/');
  await expect(page.getByText('No hay restaurantes disponibles.', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver restaurante', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Agregar al carrito', exact: true })).toBeDisabled();
  await page.unroute('**/api/catalog');
  await page.route('**/api/catalog', (route) => route.fulfill({ status: 503, json: { detail: 'Test unavailable' } }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('No se pudo cargar el catálogo');
  await expect(page.getByRole('link', { name: 'Ver restaurante', exact: true })).toHaveCount(0);
});

test('BF-04: ayuda honesta sin buscador ni contactos aparentes', async ({ page }) => {
  await login(page);
  await page.goto('/help');
  await expect(page.getByRole('heading', { name: 'Centro de Ayuda', exact: true })).toBeVisible();
  await expect(page.getByText(/no se procesan ni verifican pagos bancarios/)).toBeVisible();
  await expect(page.getByPlaceholder('Busca una pregunta o tema...')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Correo no disponible' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Atención telefónica no disponible' })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Ver mis reclamos' })).toHaveAttribute('href', '/claims');
});

test('BF-05: cierre motivado, bloqueo de publicación y reapertura', async ({ page }) => {
  const detail = await claim(page);
  await login(page, true);
  await page.goto(`/admin/claims/${detail.claim.id}`);
  await expect(page.getByRole('button', { name: 'Cerrar reclamo', exact: true })).toBeDisabled();
  await page.getByLabel('Motivo de cierre administrativo').fill('Cierre administrativo de prueba, sin decisión económica.');
  await page.getByRole('button', { name: 'Cerrar reclamo', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reabrir reclamo', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enviar respuesta al cliente', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reabrir reclamo', exact: true }).click();
  await expect(page.getByLabel('Motivo de cierre administrativo')).toBeVisible();
  const current = await (await page.request.get(`${API}/api/claims/${detail.claim.id}`, { headers: await headers(page, true) })).json();
  expect(current.claim.statusKey).toBe('IN_REVIEW');
  expect(current.claim.closedAt).toBeNull();
});
