import { defineConfig } from '@playwright/test';
import { findPython } from './scripts/python.mjs';
import { fileURLToPath } from 'node:url';
const data = fileURLToPath(new URL(`./tests/.tmp/browser-data-${Date.now()}`, import.meta.url));
export default defineConfig({
  testDir: './tests',
  testMatch: ['ui.spec.js', 'mobile.spec.js', 'share.spec.js', 'wordbook.spec.js', 'favorites.spec.js'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:8766', channel: 'msedge', headless: true, viewport: { width: 1440, height: 1080 }, reducedMotion: 'reduce' },
  webServer: {
    command: `"${findPython()}" server.py --port 8766`,
    url: 'http://127.0.0.1:8766/api/state',
    reuseExistingServer: false,
    env: { CONJUGAISON_DATA_DIR: data, PYTHONIOENCODING: 'utf-8' },
    timeout: 15000,
  },
});
