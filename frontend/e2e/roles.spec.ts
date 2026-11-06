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
  await page.getByRole('link', { name: 'Reportes' }).click();
  await expect(page.getByRole('heading', { name: 'Reportes y Analytics' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'PDF' })).toBeVisible();
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
