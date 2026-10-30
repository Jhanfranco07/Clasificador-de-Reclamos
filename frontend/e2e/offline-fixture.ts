import { test as base, expect } from '@playwright/test';
export { expect };

export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (['127.0.0.1', 'localhost'].includes(url.hostname) && ['8000', '5173'].includes(url.port)) {
        return route.continue();
      }
      return route.abort();
    });
    await use(context);
  },
});

import type { Page } from '@playwright/test';
export const API = 'http://127.0.0.1:8000';
export async function headers(page: Page, staff = false) {
  const r = await page.request.post(`${API}/api/auth/login`, { data: {
    email: staff ? 'gonzalo.caceres@smartclaim.com' : 'jhan.perez@gmail.com', password: '123456',
  } });
  expect(r.status()).toBe(200);
  return { Authorization: `Bearer ${(await r.json()).token}` };
}
export async function login(page: Page, staff = false) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(staff ? 'gonzalo.caceres@smartclaim.com' : 'jhan.perez@gmail.com');
  await page.getByLabel(/Contraseña/).fill('123456');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}
export async function claim(page: Page) {
  const client = await headers(page);
  const orders = await (await page.request.get(`${API}/api/orders`, { headers: client })).json();
  const r = await page.request.post(`${API}/api/claims`, { headers: client, data: {
    customer_name: 'Jhan Perez', customer_email: 'jhan.perez@gmail.com', order_code: orders.items[0].code,
    description: 'Me cobraron dos veces el mismo pedido', analyze: true,
  } });
  expect(r.status()).toBe(201);
  const id = (await r.json()).claim.id;
  return (await page.request.get(`${API}/api/claims/${id}`, { headers: await headers(page, true) })).json();
}
