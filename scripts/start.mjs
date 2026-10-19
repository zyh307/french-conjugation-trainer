import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { findPython } from './python.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
const dev = process.argv.includes('--dev');
if (!dev && !existsSync('dist/index.html')) {
  const built = spawnSync(process.execPath, ['node_modules/vite/bin/vite.js', 'build'], { stdio: 'inherit', windowsHide: true });
  if (built.status !== 0) process.exit(built.status || 1);
}
const children = [];
const stop = () => { for (const child of children) child.kill(); };
const api = spawn(findPython(), ['server.py', ...(process.argv.includes('--open') ? ['--open'] : [])], { cwd: root, stdio: 'inherit', windowsHide: true });
children.push(api);
api.on('exit', code => { stop(); process.exit(code || 0); });
if (dev) {
  const ui = spawn(process.execPath, ['node_modules/vite/bin/vite.js'], { cwd: root, stdio: 'inherit', windowsHide: true });
  children.push(ui);
  ui.on('exit', code => { stop(); process.exit(code || 0); });
}
process.on('SIGINT', () => { stop(); process.exit(0); });
process.on('SIGTERM', () => { stop(); process.exit(0); });
process.on('exit', stop);
console.log(`\n  法语变位器 3.0 · http://127.0.0.1:${dev ? 5173 : 8765}\n  关闭此窗口或按 Ctrl+C 停止服务。\n`);
