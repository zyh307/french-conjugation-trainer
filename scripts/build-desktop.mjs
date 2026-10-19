import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { findPython } from './python.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
for (const [command, args] of [[process.execPath, ['node_modules/vite/bin/vite.js', 'build']], [findPython(), ['scripts/build-desktop.py']]]) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
