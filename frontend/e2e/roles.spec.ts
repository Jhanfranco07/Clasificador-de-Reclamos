import { expect, Page, test } from '@playwright/test';

async function login(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
}

test('cliente navega por pedidos, reclamos y perfil', async ({ page }) => {
  await login(page, 'maria.gonzalez@email.com');
  await expect(page).toHaveURL(/\/dashboard|\/checkout/);
  await page.goto('/claims');
  await expect(page.getByRole('heading', { name: 'Mis reclamos' })).toBeVisible();
  await page.goto('/profile');
  await expect(page.getByRole('heading', { name: 'Mi perfil' })).toBeVisible();
});

test('agente gestiona reclamos sin acceder a configuración administrativa', async ({ page }) => {
  await login(page, 'laura.martinez@smartclaim.com');
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
