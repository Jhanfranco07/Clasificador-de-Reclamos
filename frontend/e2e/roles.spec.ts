import { readFile } from 'node:fs/promises';
import { expect, Page, test } from '@playwright/test';

async function login(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
}

test('cliente navega por pedidos, reclamos y perfil', async ({ page }) => {
  await login(page, 'jhan.perez@gmail.com');
  await expect(page).toHaveURL(/\/dashboard|\/checkout/);
  await page.goto('/claims');
  await expect(page.getByRole('heading', { name: 'Mis reclamos' })).toBeVisible();
  await page.getByRole('button', { name: 'Abrir menú de cuenta' }).click();
  await expect(page.getByRole('button', { name: 'Editar perfil' })).toBeVisible();
  await page.getByRole('button', { name: 'Editar perfil' }).click();
  await expect(page.getByRole('heading', { name: 'Mi perfil' })).toBeVisible();
});

test('cliente vuelve a la pantalla que originó el inicio de sesión', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Iniciar sesión' }).click();
  await page.getByLabel('Email').fill('jhan.perez@gmail.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).toHaveURL('/');
});

test('preferencia de tema oscuro persiste al recargar', async ({ page }) => {
  await login(page, 'jhan.perez@gmail.com');
  await page.getByRole('button', { name: 'Usar tema oscuro' }).click();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await expect(page.getByRole('button', { name: 'Usar tema claro' })).toBeVisible();
});

test('agente gestiona reclamos sin acceder a configuración administrativa', async ({ page }) => {
  await login(page, 'gonzalo.caceres@smartclaim.com');
  await expect(page).toHaveURL(/\/admin/);
  await expect(page.getByRole('link', { name: 'Bandeja de reclamos' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Configuración IA' })).toHaveCount(0);
  await page.goto('/admin/knowledge');
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto('/admin/ai-config');
  await expect(page).toHaveURL(/\/admin$/);
});

test('administrador accede a reportes y base documental', async ({ page }) => {
  await login(page, 'admin@smartclaim.com');
  const reportsRequest = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/reports' && response.request().method() === 'GET');
  await page.getByRole('link', { name: 'Reportes' }).click();
  expect((await reportsRequest).ok()).toBeTruthy();
  await expect(page.getByRole('heading', { name: 'Reportes y Analytics' })).toBeVisible();
  const pdfDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'PDF', exact: true }).click();
  const pdf = await pdfDownload;
  expect(pdf.suggestedFilename()).toMatch(/\.pdf$/);
  expect((await readFile((await pdf.path())!)).subarray(0, 5).toString()).toBe('%PDF-');
  const csvDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'CSV', exact: true }).click();
  const csv = await csvDownload;
  expect(csv.suggestedFilename()).toMatch(/\.csv$/);
  expect((await readFile((await csv.path())!, 'utf8')).trim().split(/\r?\n/).length).toBeGreaterThan(1);
  await page.getByRole('link', { name: 'Base documental' }).click();
  await expect(page.getByRole('heading', { name: 'Base documental' })).toBeVisible();
});


function textPdf() {
  const text = 'BT /F1 12 Tf 20 200 Td (Revisar el recibo por un producto faltante.) Tj ET';
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Length ' + text.length + ' >>\nstream\n' + text + '\nendstream',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = objects.map((object, index) => {
    const offset = pdf.length;
    pdf += (index + 1) + ' 0 obj\n' + object + '\nendobj\n';
    return offset;
  });
  const xref = pdf.length;
  pdf += 'xref\n0 6\n0000000000 65535 f \n';
  for (const offset of offsets) pdf += String(offset).padStart(10, '0') + ' 00000 n \n';
  return Buffer.from(pdf + 'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n' + xref + '\n%%EOF\n');
}

test('administrador registra texto y revisa PDF desde un móvil', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'admin@smartclaim.com');
  await expect(page).toHaveURL(/\/admin/);
  await page.goto('/admin/knowledge');
  const file = page.getByLabel('Importar PDF para revisión');
  const title = page.getByPlaceholder('Titulo del documento');
  const content = page.getByPlaceholder('Contenido que alimentara las respuestas del sistema');
  const save = page.getByRole('button', { name: 'Agregar documento' });
  const runId = Date.now();
  const manualTitle = 'Registro manual Playwright ' + runId;
  const pdfTitle = 'PDF importado Playwright ' + runId;
  await title.fill(manualTitle);
  await content.fill('Contenido manual para la prueba de registro administrativo. ' + runId);
  await save.click();
  await expect(page.getByText(manualTitle, { exact: true })).toBeVisible();

  await file.setInputFiles({ name: 'texto.txt', mimeType: 'application/pdf', buffer: textPdf() });
  await expect(page.getByText(/extensión \.pdf/)).toBeVisible();
  await file.setInputFiles({ name: 'dañado.pdf', mimeType: 'application/pdf', buffer: Buffer.from('bad') });
  await expect(page.getByText(/cabecera PDF válida/)).toBeVisible();

  let releasePreview!: () => void;
  const previewGate = new Promise<void>((resolve) => { releasePreview = resolve; });
  await page.route('**/api/documents/pdf-preview', async (route) => {
    await previewGate;
    await route.continue();
  }, { times: 1 });
  await file.setInputFiles({ name: 'ejemplo.pdf', mimeType: 'application/pdf', buffer: textPdf() });
  await expect(save).toBeDisabled();
  await expect(page.getByRole('status')).toContainText('Extrayendo texto del PDF');
  releasePreview();
  await expect(content).toHaveValue('Revisar el recibo por un producto faltante.');
  await page.getByRole('button', { name: 'Cancelar PDF' }).click();
  await expect(content).toHaveValue('');
  await file.setInputFiles({ name: 'ejemplo.pdf', mimeType: 'application/pdf', buffer: textPdf() });
  await expect(content).toHaveValue('Revisar el recibo por un producto faltante.');
  await page.getByRole('combobox', { name: 'Categoría documental' }).click();
  await page.getByRole('option', { name: 'Producto incompleto', exact: true }).click();
  await content.fill('Revisar el recibo por un producto faltante. ' + runId);
  await title.fill(pdfTitle);
  await save.click();
  await expect(page.getByText(pdfTitle, { exact: true })).toBeVisible();
  await page.getByPlaceholder(/Buscar/).fill(pdfTitle);
  await expect(page.getByText(manualTitle, { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Reindexar', exact: true }).click();
  await expect(page.getByText(/Índice TF-IDF reconstruido correctamente/)).toBeVisible();
});


test('cliente compra y recibe la respuesta solo después de revisión humana', async ({ page, browser }) => {
  await login(page, 'jhan.perez@gmail.com');
  await expect(page).toHaveURL(/\/dashboard/);
  await page.goto('/restaurants/1');
  await expect(page.getByRole('heading', { name: 'Criollo Peruano' })).toBeVisible();
  await page.getByRole('button', { name: /Agregar Lomo/ }).click();
  await page.goto('/cart');
  await page.getByRole('button', { name: 'Continuar al pago' }).click();
  await page.getByLabel('Dirección de entrega').fill('Dirección ficticia de la demo');
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: 'Efectivo', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmar pedido', exact: true }).click();
  await expect(page).toHaveURL(/\/orders\/\d+$/);
  const orderId = new URL(page.url()).pathname.split('/').pop();
  await page.goto('/claims/new?orderId=' + orderId);
  await page.getByLabel(/Descripción del problema/).fill(
    'Mi pedido llegó incompleto. Faltan productos pagados y tengo el recibo del pedido.',
  );
  const create = page.waitForResponse((response) =>
    response.url().endsWith('/api/claims') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Enviar reclamo' }).click();
  const created = await create;
  expect(created.status()).toBe(201);
  const detail = await created.json();
  expect(detail.response).toBeNull();
  await expect(page.getByRole('heading', { name: 'Reclamo recibido' })).toBeVisible();

  const staff = await browser.newPage();
  try {
    await login(staff, 'gonzalo.caceres@smartclaim.com');
    await expect(staff).toHaveURL(/\/admin/);
    await staff.goto('/admin/claims/' + detail.claim.id);
    await expect(staff.getByRole('heading', { name: /FAQ sobre pedido incompleto/ })).toBeVisible();
    await staff.getByRole('button', { name: 'Editar respuesta' }).click();
    const reply = 'Verificaremos los artículos faltantes con el comprobante del pedido.';
    await staff.locator('textarea').first().fill(reply);
    await staff.getByRole('button', { name: 'Guardar edicion' }).click();
    await expect(staff.getByText(reply, { exact: true })).toBeVisible();
    await page.goto('/claims/' + detail.claim.id);
    await expect(page.getByRole('heading', { name: 'Reclamo ' + detail.claim.code })).toBeVisible();
    await expect(page.getByText(reply, { exact: false })).toHaveCount(0);
    await expect(page.getByText('Respuesta publicada', { exact: true })).toHaveCount(0);
    await staff.getByRole('button', { name: 'Escalar', exact: true }).click();
    await expect(staff.getByText('Escalado', { exact: true }).first()).toBeVisible();
    await staff.getByRole('button', { name: 'Enviar respuesta al cliente' }).click();
    await expect(staff.getByText('Respondido', { exact: true }).first()).toBeVisible();
    await page.reload();
    await expect(page.getByText(reply, { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Respuesta publicada', { exact: true })).toHaveCount(1);
    await expect(page.getByText('Caso derivado', { exact: true })).toBeVisible();
  } finally {
    await staff.close();
  }
});
