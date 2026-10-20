import { spawnSync } from 'node:child_process';
import { mkdirSync, existsSync, readFileSync, writeFileSync, readdirSync, copyFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes, createHash } from 'node:crypto';
import { findPython } from './python.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
// Keep native tool arguments relative and ASCII: aapt2 on Windows rejects some Unicode paths.
const tools = '.android-tools/build-tools/android-15';
const platform = '.android-tools/platform/android-35/android.jar';
const javaBin = process.env.JAVA_HOME ? join(process.env.JAVA_HOME, 'bin') : 'D:/bin';
const build = 'android/build';
const output = join(root, '手机安装包');
function run(command, args, extra = {}) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit', windowsHide: true, ...extra });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed (${result.status})`);
}
for (const required of [platform, join(tools, 'aapt2.exe'), join(javaBin, 'javac.exe')]) if (!existsSync(required)) throw new Error(`Android build dependency missing: ${required}`);
for (const folder of [build, output, join(build, 'classes'), join(build, 'dex'), join(root, '.android-tools/signing')]) mkdirSync(folder, { recursive: true });
run(process.execPath, ['scripts/export-wordlists.mjs']);
run(process.execPath, ['node_modules/vite/bin/vite.js', 'build', '--mode', 'mobile', '--outDir', 'dist-mobile']);
run(join(tools, 'aapt2.exe'), ['compile', '--dir', 'android/res', '-o', join(build, 'resources.zip')]);
run(join(tools, 'aapt2.exe'), ['link', '-o', join(build, 'resources.apk'), '--manifest', 'android/AndroidManifest.xml', '-I', platform, '-A', 'dist-mobile', '--auto-add-overlay', join(build, 'resources.zip')]);
run(join(javaBin, 'javac.exe'), ['-source', '8', '-target', '8', '-Xlint:-options', '-encoding', 'UTF-8', '-bootclasspath', platform, '-d', join(build, 'classes'), 'android/src/cn/zyh307/conjugaison/MainActivity.java', 'android/src/cn/zyh307/conjugaison/ShareImageProvider.java']);
const classes = [];
function collect(directory) { for (const entry of readdirSync(directory, { withFileTypes: true })) { const path = join(directory, entry.name); if (entry.isDirectory()) collect(path); else if (entry.name.endsWith('.class')) classes.push(path); } }
collect(join(build, 'classes'));
run(join(javaBin, 'java.exe'), ['-cp', join(tools, 'lib/d8.jar'), 'com.android.tools.r8.D8', '--min-api', '26', '--lib', platform, '--output', join(build, 'dex'), ...classes]);
run(findPython(), ['-c', `from zipfile import ZipFile,ZIP_DEFLATED\nfrom pathlib import Path\np=Path(r'${build}')\nwith ZipFile(p/'resources.apk','a',ZIP_DEFLATED) as z:\n z.write(p/'dex/classes.dex','classes.dex')`]);
run(join(tools, 'zipalign.exe'), ['-f', '-p', '4', join(build, 'resources.apk'), join(build, 'aligned.apk')]);
const secretPath = join(root, '.android-tools/signing/local.json');
const store = join(root, '.android-tools/signing/conjugaison.jks');
let secret;
if (existsSync(secretPath)) secret = JSON.parse(readFileSync(secretPath, 'utf8'));
else { secret = { password: randomBytes(32).toString('hex') }; writeFileSync(secretPath, JSON.stringify(secret)); }
const env = { ...process.env, CONJUGAISON_STORE_PASS: secret.password };
if (!existsSync(store)) run(join(javaBin, 'keytool.exe'), ['-genkeypair', '-keystore', store, '-alias', 'conjugaison', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-storepass:env', 'CONJUGAISON_STORE_PASS', '-keypass:env', 'CONJUGAISON_STORE_PASS', '-dname', 'CN=Conjugaison Local,OU=Personal,O=Conjugaison,C=CN'], { env });
const apk = join(output, '法语变位器-3.1.0.apk');
run(join(javaBin, 'java.exe'), ['-jar', join(tools, 'lib/apksigner.jar'), 'sign', '--ks', store, '--ks-key-alias', 'conjugaison', '--ks-pass', 'env:CONJUGAISON_STORE_PASS', '--key-pass', 'env:CONJUGAISON_STORE_PASS', '--out', apk, join(build, 'aligned.apk')], { env });
run(join(javaBin, 'java.exe'), ['-jar', join(tools, 'lib/apksigner.jar'), 'verify', '--verbose', '--print-certs', apk]);
const hash = createHash('sha256').update(readFileSync(apk)).digest('hex');
writeFileSync(join(output, 'SHA256.txt'), `${hash}  法语变位器-3.1.0.apk\n`);
console.log(`\nAPK ready: ${apk}\nSHA-256: ${hash}`);
