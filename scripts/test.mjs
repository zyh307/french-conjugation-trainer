import { spawnSync } from 'node:child_process';
import { findPython } from './python.mjs';
const result = spawnSync(findPython(), ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], { stdio: 'inherit', windowsHide: true });
process.exit(result.status || 0);
