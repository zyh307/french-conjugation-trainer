import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

export function findPython() {
  const bundled = 'D:/deepseek/resources/runtime/primary-runtime/dependencies/python/python.exe';
  const candidates = [process.env.CONJUGAISON_PYTHON, ...(existsSync(bundled) ? [bundled] : []), 'python3', 'python', 'py'];
  for (const command of candidates.filter(Boolean)) {
    const result = spawnSync(command, ['-c', 'import sys; print(sys.version_info.major)'], { encoding: 'utf8', timeout: 5000, windowsHide: true });
    if (result.status === 0 && result.stdout.trim() === '3') return command;
  }
  throw new Error('需要 Python 3.10+。安装 Python，或设置 CONJUGAISON_PYTHON 为 python 可执行文件路径。');
}
