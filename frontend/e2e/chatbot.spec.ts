import { expect, login, test, API } from './offline-fixture';

test('el asistente inicia tras acceder, recomienda desde el catálogo y confirma el carrito', async ({ page }) => {
  await login(page);
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

test('el lanzador del asistente se mantiene accesible en todas las secciones del cliente', async ({ page }) => {
  await login(page);
  await expect(page).toHaveURL(/\/restaurants$/);
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await expect(chat).toBeVisible();
  await chat.getByRole('button', { name: 'Minimizar chat' }).click();

  for (const path of ['/restaurants', '/dashboard', '/cart', '/orders', '/claims', '/help']) {
    await page.goto(path);
    await expect(page.getByRole('button', { name: 'Abrir ayuda' })).toBeVisible();
  }
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Abrir ayuda' })).toHaveCount(0);
});

test('el asistente permanece oculto para visitantes y los pedidos exigen sesión', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('region', { name: 'Asistente SmartClaim AI' })).toHaveCount(0);
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Abrir ayuda' })).toHaveCount(0);
  const orders = await page.request.get(`${API}/api/orders`);
  expect(orders.status()).toBe(401);
});

test('respeta el cierre después de iniciar sesión y oculta el chat en login', async ({ page }) => {
  await login(page);
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await expect(chat).toBeVisible();
  await chat.getByRole('button', { name: 'Minimizar chat' }).click();
  await page.goto('/claims');
  await expect(chat).toHaveCount(0);
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Abrir ayuda' })).toHaveCount(0);
});

test('el chat cabe en una pantalla móvil', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 667 });
  await login(page);
  const chat = page.getByRole('region', { name: 'Asistente SmartClaim AI' });
  await expect(chat).toBeVisible();
  const box = await chat.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(box!.y + box!.height).toBeLessThanOrEqual(667);
  await expect(chat.getByLabel('Escribe tu mensaje')).toBeVisible();
});

test('el panel se minimiza al cambiar de sección y deja utilizar sus controles', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 667 });
  await login(page);
  await expect(page.getByRole('region', { name: 'Asistente SmartClaim AI' })).toBeVisible();
  await page.goto('/claims');
  await expect(page.getByRole('region', { name: 'Asistente SmartClaim AI' })).toHaveCount(0);
  await page.evaluate(() => {
    const button = document.createElement('button');
    button.id = 'under-chat-control';
    button.textContent = 'Control de la página';
    button.style.cssText = 'position:fixed;right:80px;bottom:250px;z-index:1';
    button.addEventListener('click', () => button.dataset.clicked = 'yes');
    document.body.appendChild(button);
  });
  await page.locator('#under-chat-control').click();
  await expect(page.locator('#under-chat-control')).toHaveAttribute('data-clicked', 'yes');
});
