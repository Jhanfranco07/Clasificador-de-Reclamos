import { expect, test } from './offline-fixture';

test('el asistente inicia, recomienda desde el catálogo y confirma el carrito', async ({ page }) => {
  await page.goto('/');
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await expect(chat).toBeVisible();
  await expect(chat.getByText(/Soy tu asistente de compras/)).toBeVisible();
  await chat.getByRole('button', { name: 'Recomendar platos' }).click();
  const recommendation = chat.getByRole('button', { name: 'Agregar', exact: true }).first();
  await expect(recommendation).toBeVisible();
  await recommendation.click();
  await expect(chat.getByRole('button', { name: 'Confirmar' })).toBeVisible();
  await chat.getByRole('button', { name: 'Confirmar' }).click();
  await expect(chat.getByRole('status')).toContainText('agregado al carrito');
  const product = chat.getByRole('link', { name: 'Ver producto' }).first();
  await product.click();
  await expect(page).toHaveURL(/\/restaurants\/\d+#product-\d+/);
  await expect(chat.getByText(/Soy tu asistente de compras/)).toBeVisible();
  await chat.getByRole('button', { name: 'Cerrar chat' }).click();
  await expect(chat).toHaveCount(0);
  await page.getByRole('link', { name: /Ver carrito/ }).first().click();
  await expect(chat).toHaveCount(0);
});

test('el asistente no muestra pedidos propios a visitantes', async ({ page }) => {
  await page.goto('/');
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await chat.getByRole('button', { name: 'Consultar pedidos' }).click();
  await expect(chat.getByText(/necesitas iniciar sesión/)).toBeVisible();
});

test('respeta el cierre durante el inicio de sesión', async ({ page }) => {
  await page.goto('/');
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await chat.getByRole('button', { name: 'Minimizar chat' }).click();
  await page.goto('/login');
  await page.getByLabel('Email').fill('jhan.perez@gmail.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await expect(chat).toHaveCount(0);
});

test('el chat cabe en una pantalla móvil', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 667 });
  await page.goto('/');
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await expect(chat).toBeVisible();
  const box = await chat.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(box!.y + box!.height).toBeLessThanOrEqual(667);
  await expect(chat.getByLabel('Escribe tu mensaje')).toBeVisible();
});
