import type { Page } from '@playwright/test';
import { test, expect, API, login } from './offline-fixture';
import { parseCart } from '../src/app/lib/cart';

const KEY = 'smartclaim_pending_cart';
async function admin(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill('admin@smartclaim.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

test('BF-16 unidad: esquema de carrito valida tipos, cantidades y duplicados', () => {
  const valid = { id: '1', name: 'Producto', restaurantName: 'Comercio', quantity: 1, price: 1, image: '' };
  for (const raw of ['{invalid', 'null', '{}', '"text"', '[null]', '[{}]', JSON.stringify([{ ...valid, quantity: -1 }]),
    JSON.stringify([{ ...valid, quantity: true }]), JSON.stringify([{ ...valid, quantity: 1.5 }]),
    JSON.stringify([{ ...valid, id: '-1' }]), JSON.stringify([{ ...valid, name: '' }]),
    JSON.stringify([{ ...valid, price: '1' }]), JSON.stringify([valid, valid])]) {
    expect(parseCart(raw).blocked).toBe(true);
  }
  expect(parseCart(null).items).toEqual([]);
  expect(parseCart(JSON.stringify([valid])).items).toEqual([valid]);
});

for (const path of ['/', '/restaurants/1', '/cart', '/checkout']) {
  test(`BF-16 carrito corrupto preservado y restablecimiento explícito en ${path}`, async ({ page }) => {
    await login(page);
    await page.evaluate((key) => localStorage.setItem(key, '{invalid-json'), KEY);
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(path);
    await expect(page.getByRole('alert').filter({ hasText: 'datos inválidos' })).toBeVisible();
    expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe('{invalid-json');
    await page.getByRole('button', { name: 'Restablecer carrito' }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'datos inválidos' })).toHaveCount(0);
    expect(JSON.parse((await page.evaluate((key) => localStorage.getItem(key), KEY))!)).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test('BF-16 almacenamiento denegado no rompe la navegación', async ({ page }) => {
  await page.addInitScript((key) => {
    const read = Storage.prototype.getItem;
    Storage.prototype.getItem = function (name) { if (name === key) throw new DOMException('Denied', 'SecurityError'); return read.call(this, name); };
  }, KEY);
  await page.goto('/cart');
  await expect(page.getByRole('heading', { name: 'Tu carrito' })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('almacenamiento');
});

test('BF-16 fallo al guardar carrito informa error y no simula artículo agregado', async ({ page }) => {
  await page.addInitScript((key) => {
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function (name, value) { if (name === key) throw new DOMException('Quota', 'QuotaExceededError'); return write.call(this, name, value); };
  }, KEY);
  await page.goto('/restaurants/1');
  await page.getByRole('button', { name: /^Agregar / }).first().click();
  await expect(page.getByRole('alert')).toContainText('No se pudo guardar');
  await expect(page.getByRole('status').filter({ hasText: 'agregado' })).toHaveCount(0);
});

test('BF-16 visitante compra conservando carrito y destino, luego navega pedidos y reclamos', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Ver restaurante', exact: true }).first().click();
  await page.getByRole('button', { name: /^Agregar / }).first().click();
  await expect(page.getByRole('link', { name: 'Ver carrito (1)' })).toBeVisible();
  await page.getByRole('link', { name: /Ver carrito/ }).click();
  await page.getByRole('button', { name: 'Iniciar sesión y pagar' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Email').fill('jhan.perez@gmail.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).toHaveURL(/\/checkout$/);
  await expect(page.getByRole('button', { name: 'Confirmar pedido', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Confirmar pedido', exact: true }).click();
  await expect(page).toHaveURL(/\/orders\/\d+$/);
  await page.getByRole('link', { name: 'Mis pedidos', exact: true }).click();
  await page.getByRole('link', { name: 'Reportar problema', exact: true }).first().click();
  await expect(page).toHaveURL(/\/claims\/new\?orderId=/);
  await expect(page.getByRole('combobox')).not.toContainText('Selecciona un pedido');
  await page.getByLabel('Descripción del problema *').fill('Incidente de prueba de navegación sobre mi pedido.');
  await page.getByRole('button', { name: 'Enviar reclamo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Reclamo recibido' })).toBeVisible();
  await page.getByRole('button', { name: 'Ver mis reclamos', exact: true }).click();
  await expect(page).toHaveURL(/\/claims$/);
});

for (const entry of [
  { path: '/orders', api: '**/api/orders', empty: 'No tienes pedidos' },
  { path: '/claims', api: '**/api/claims?*', empty: 'No hay reclamos registrados' },
  { path: '/claims/new', api: '**/api/orders', empty: 'No tienes pedidos disponibles para registrar un reclamo.' },
  { path: '/dashboard', api: '**/api/orders', empty: 'Aún no tienes pedidos' },
]) {
  test(`BF-16 API 503 se distingue de vacío en ${entry.path}`, async ({ page }) => {
    await login(page);
    await page.route(entry.api, (route) => route.fulfill({ status: 503, json: { detail: 'Servicio de prueba no disponible' } }));
    await page.goto(entry.path);
    await expect(page.getByRole('alert').first()).toBeVisible();
    await expect(page.getByText(entry.empty, { exact: true })).toHaveCount(0);
    if (entry.path === '/claims/new') {
      await expect(page.getByRole('button', { name: 'Enviar reclamo', exact: true })).toBeDisabled();
      await page.unroute(entry.api);
      await page.getByRole('button', { name: 'Reintentar carga de pedidos' }).click();
      await expect(page.getByRole('alert')).toHaveCount(0);
      await expect(page.getByRole('combobox')).toBeEnabled();
    }
  });
}

test('BF-16 artículo retirado bloquea compra sin perder carrito', async ({ page }) => {
  await page.goto('/restaurants/1');
  await page.getByRole('button', { name: /^Agregar / }).first().click();
  await page.route('**/api/orders/quote', (route) => route.fulfill({ status: 422, json: { detail: 'Producto o establecimiento no disponible' } }));
  await page.getByRole('link', { name: /Ver carrito/ }).click();
  await expect(page.getByRole('alert')).toContainText('no disponible');
  await expect(page.getByRole('button', { name: 'Iniciar sesión y pagar' })).toBeDisabled();
  expect(JSON.parse((await page.evaluate((key) => localStorage.getItem(key), KEY))!)).toHaveLength(1);
});

test('BF-14 guardar todos los valores y confirmar con una nueva consulta', async ({ page }) => {
  await admin(page);
  await page.goto('/admin/ai-config');
  await expect(page.getByRole('button', { name: 'Guardar configuración', exact: true })).toBeEnabled();
  const rag = page.getByLabel('Habilitar RAG');
  if (await rag.getAttribute('aria-checked') !== 'true') await rag.click();
  const slider = page.getByRole('slider');
  await slider.focus();
  await page.keyboard.press('Home');
  await expect(slider).toHaveAttribute('aria-valuenow', '0');
  await page.getByLabel('Número de documentos a recuperar').click();
  await page.getByRole('option', { name: '10 documento(s)', exact: true }).click();
  const human = page.getByLabel('Revisión humana obligatoria');
  if (await human.getAttribute('aria-checked') !== 'false') await human.click();
  const verified = page.waitForResponse((r) => r.url().endsWith('/api/config') && r.request().method() === 'GET');
  await page.getByRole('button', { name: 'Guardar configuración', exact: true }).click();
  const actual = await (await verified).json();
  expect(actual.confidenceThreshold).toBe(0);
  expect(actual.maxDocuments).toBe(10);
  expect(actual.humanReviewRequired).toBe(false);
  expect(actual.useRag).toBe(true);
  await expect(page.getByText(/Configuración guardada/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole('slider')).toHaveAttribute('aria-valuenow', '0');
  await expect(page.getByLabel('Número de documentos a recuperar')).toContainText('10 documento(s)');
  await expect(page.getByText(/Modelo configurado:/)).toBeVisible();
  await expect(page.getByText(/Última clasificación ejecutada registrada:|No hay una ejecución reciente/)).toBeVisible();
});

test('BF-14 no anuncia éxito si PUT responde 200 pero la nueva consulta no confirma', async ({ page }) => {
  await admin(page);
  await page.goto('/admin/ai-config');
  await expect(page.getByRole('button', { name: 'Guardar configuración', exact: true })).toBeEnabled();
  await page.getByLabel('Habilitar RAG').click();
  await page.route('**/api/config', (route) => route.request().method() === 'PUT' ? route.fulfill({ json: {} }) : route.continue());
  await page.getByRole('button', { name: 'Guardar configuración', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'no coincide' })).toBeVisible();
  await expect(page.getByText(/Configuración guardada/)).toHaveCount(0);
});

for (const width of [320, 360, 768, 1280]) {
  test(`BF-16 pantallas sin desbordamiento global a ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('link', { name: 'Ver restaurante', exact: true }).first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await login(page);
    for (const path of ['/orders', '/claims', '/claims/new', '/restaurants/1', '/cart']) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await page.waitForLoadState('networkidle');
      expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(width);
    }
    await admin(page);
    for (const path of ['/admin/knowledge', '/admin/ai-config']) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await page.waitForLoadState('networkidle');
      expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(width);
    }
    await page.screenshot({ path: info.outputPath(`config-${width}.png`), fullPage: true });
  });
}

test('BF-16 nombres, códigos e importes largos conservan acciones a 320px', async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await login(page);
  const orders = await (await page.request.get(`${API}/api/orders`, { headers: {
    Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('smartclaim_token'))}`,
  } })).json();
  orders.items[0].storeName = 'Establecimiento '.repeat(12);
  orders.items[0].code = 'ORD-' + 'X'.repeat(90);
  orders.items[0].total = 1234567890.12;
  await page.route('**/api/orders', (r) => r.fulfill({ json: orders }));
  await page.goto('/orders');
  await expect(page.getByText(orders.items[0].code)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.getByRole('link', { name: 'Ver detalle', exact: true }).first().click();
  await expect(page).toHaveURL(/\/orders\/\d+$/);
  await admin(page);
  await page.route('**/api/documents', async (r) => {
    const response = await r.fetch();
    const data = await response.json();
    data.items[0].title = 'Documento'.repeat(30);
    data.items[0].content = 'Contenido'.repeat(50);
    await r.fulfill({ json: data });
  });
  await page.goto('/admin/knowledge');
  await expect(page.getByText('Documento'.repeat(30), { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.getByRole('button', { name: 'Editar', exact: true }).first().click();
  await expect(page.getByPlaceholder('Titulo del documento')).toHaveValue('Documento'.repeat(30));
  await page.screenshot({ path: info.outputPath('knowledge-long-320.png'), fullPage: true });
});

test('BF-14 error inicial deja edición bloqueada y permite recargar', async ({ page }) => {
  await admin(page);
  await page.route('**/api/config', (r) => r.fulfill({ status: 503, json: { detail: 'Configuración temporalmente no disponible' } }));
  await page.goto('/admin/ai-config');
  await expect(page.getByRole('alert').filter({ hasText: 'no disponible' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Guardar configuración', exact: true })).toBeDisabled();
  await page.unroute('**/api/config');
  await page.getByRole('button', { name: 'Recargar configuración' }).click();
  await expect(page.getByRole('button', { name: 'Guardar configuración', exact: true })).toBeEnabled();
});

test('BF-16 conversación con error no aparenta historial vacío y permite reintentar', async ({ page }) => {
  await login(page);
  const token = await page.evaluate(() => localStorage.getItem('smartclaim_token'));
  const claims = await (await page.request.get(`${API}/api/claims`, { headers: { Authorization: `Bearer ${token}` } })).json();
  const id = claims.items[0].id;
  await page.route(`**/api/claims/${id}/messages`, (r) => r.fulfill({ status: 503, json: { detail: 'No disponible' } }));
  await page.goto(`/claims/${id}`);
  await expect(page.getByRole('alert').filter({ hasText: 'conversación' })).toBeVisible();
  await expect(page.getByText('No hay mensajes registrados.', { exact: true })).toHaveCount(0);
  await page.unroute(`**/api/claims/${id}/messages`);
  await page.getByRole('button', { name: 'Reintentar conversación' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'conversación' })).toHaveCount(0);
});

for (const entry of [
  { path: '/admin', api: '**/api/dashboard' },
  { path: '/admin/reports', api: '**/api/reports**' },
  { path: '/admin/claims', api: '**/api/claims?*' },
  { path: '/admin/knowledge', api: '**/api/documents' },
]) {
  test(`BF-16 error administrativo visible sin datos vacíos en ${entry.path}`, async ({ page }) => {
    await admin(page);
    await page.route(entry.api, (r) => r.fulfill({ status: 503, json: { detail: 'Servicio administrativo no disponible' } }));
    await page.goto(entry.path);
    await expect(page.getByRole('alert').first()).toBeVisible();
    await expect(page.getByText('No hay reclamos con este filtro', { exact: true })).toHaveCount(0);
    await expect(page.getByText('No hay documentos registrados.', { exact: true })).toHaveCount(0);
  });
}

for (const resource of ['orders', 'claims']) {
  test(`BF-16 detalle ${resource} distingue 503 de inexistencia`, async ({ page }) => {
    await login(page);
    await page.route(`**/api/${resource}/999999`, (r) => r.fulfill({ status: 503, json: { detail: 'Servicio temporalmente no disponible' } }));
    await page.goto(`/${resource}/999999`);
    await expect(page.getByRole('alert').filter({ hasText: 'temporalmente' })).toBeVisible();
    await expect(page.getByRole('heading', { name: /No se pudo cargar/ })).toBeVisible();
  });
}

test('BF-16 destacado sin productos no agrega artículos fantasma', async ({ page }) => {
  await page.route('**/api/catalog', (r) => r.fulfill({ json: { items: [{ id: '1', name: 'Sin productos', category: 'Prueba', products: [] }] } }));
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Agregar al carrito', exact: true })).toBeDisabled();
  await expect(page.getByText('Sin producto destacado', { exact: true })).toBeVisible();
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBeNull();
});
