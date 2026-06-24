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
