import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
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

test('bare review route links to open curation pull requests', async ({ page }) => {
  const configuration = JSON.parse(
    await readFile(path.join(pagesRoot, 'review', 'config.json'), 'utf8'),
  );
  const expected = new URL(
    `/${configuration.repository}/pulls`,
    'https://github.com',
  );
  expected.searchParams.set('q', 'is:pr is:open label:curation-review');

  const response = await page.goto(
    new URL(`${fixture.mount}review/`, fixture.origin).href,
  );
  expect(response?.status()).toBe(200);
  await expect(page.getByRole('link', {
    name: 'View open curation pull requests on GitHub',
  })).toHaveAttribute('href', expected.href);
});

test('structured taxonomy presentation keeps filters and list variants', async ({ page }) => {
  let response = await page.goto(
    new URL(`${fixture.mount}publications/`, fixture.origin).href,
  );
  expect(response?.status()).toBe(200);
  await expect(page.locator('[data-orinoco-taxonomy]')).toBeVisible();
  await expect(page.locator('#orinoco-search')).toBeVisible();
  await expect(page.locator('[data-orinoco-count]')).toContainText(/results?$/);

  response = await page.goto(
    new URL(`${fixture.mount}instruments/`, fixture.origin).href,
  );
  expect(response?.status()).toBe(200);
  await expect(page.locator('.orinoco-grid')).toBeVisible();
});
