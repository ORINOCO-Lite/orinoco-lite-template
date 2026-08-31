import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { startStaticServer } from './static-server.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const pagesRoot = path.resolve(
  ROOT,
  process.env.ORINOCO_PAGES_ROOT ?? 'build/pages',
);
const projectPath = process.env.ORINOCO_PROJECT_PATH ?? '/orinoco-site/';

let fixture;

test.beforeAll(async () => {
  fixture = await startStaticServer(pagesRoot, projectPath);
});

test.afterAll(async () => {
  await fixture.close();
});

test('project-path root is a navigable static page', async ({ page }) => {
  const response = await page.goto(new URL(fixture.mount, fixture.origin).href);
  expect(response?.status()).toBe(200);
  await expect(page.locator('html')).toBeVisible();
  await expect(page.locator('body')).not.toBeEmpty();
  expect(new URL(page.url()).pathname.startsWith(fixture.mount)).toBeTruthy();
});

test('root-relative assets remain under the project path', async ({ page }) => {
  await page.goto(new URL(fixture.mount, fixture.origin).href);
  const localResources = await page.locator('[href], [src]').evaluateAll(
    (elements, origin) => elements
      .map((element) => element.getAttribute('href') ?? element.getAttribute('src'))
      .filter((value) => value !== null)
      .map((value) => new URL(value, window.location.href))
      .filter((url) => url.origin === origin)
      .map((url) => url.pathname),
    fixture.origin,
  );
  for (const resource of localResources) {
    expect(resource.startsWith(fixture.mount), resource).toBeTruthy();
  }
});
