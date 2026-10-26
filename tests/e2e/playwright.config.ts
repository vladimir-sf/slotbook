import { defineConfig } from '@playwright/test';
import { lstatSync, realpathSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

// Raw JUnit/browser working files belong ONLY in an owner-only directory outside the checkout.
const privateDir = process.env.SLOTBOOK_QA_PRIVATE_DIR;
if (!privateDir || !path.isAbsolute(privateDir)) throw new Error('qa_guard:private_directory_required');
const source = path.resolve(__dirname, '../..');
try {
  const resolved = realpathSync(privateDir);
  const info = lstatSync(privateDir);
  if (resolved !== privateDir || !info.isDirectory() || info.uid !== os.userInfo().uid ||
      (info.mode & 0o077) !== 0 || resolved === source || resolved.startsWith(source + path.sep)) {
    throw new Error();
  }
} catch {
  throw new Error('qa_guard:unsafe_private_directory');
}
// Playwright resolves these environment variables BEFORE reporter.outputFile.
if (['PLAYWRIGHT_JUNIT_OUTPUT_FILE', 'PLAYWRIGHT_JUNIT_OUTPUT_DIR', 'PLAYWRIGHT_JUNIT_OUTPUT_NAME']
    .some(key => process.env[key] !== undefined)) throw new Error('qa_guard:report_override_forbidden');
for (const [name, directory] of [['e2e.xml', false], ['browser-work', true]] as const) {
  try {
    const info = lstatSync(path.join(privateDir, name));
    if (info.isSymbolicLink() || info.uid !== os.userInfo().uid || (info.mode & 0o077) !== 0 ||
        (directory ? !info.isDirectory() : !info.isFile())) throw new Error();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw new Error('qa_guard:unsafe_private_output');
  }
}
if (!/^[0-9a-f]{64}$/.test(process.env.SLOTBOOK_CANDIDATE_SHA256 ?? '')) {
  throw new Error('qa_guard:candidate_required');
}
process.umask(0o077);

export default defineConfig({
  testDir: __dirname,
  testMatch: '**/*.spec.ts',
  forbidOnly: true,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  outputDir: path.join(privateDir, 'browser-work'),
  reporter: [['junit', { outputFile: path.join(privateDir, 'e2e.xml'), stripANSIControlSequences: true }]],
  use: {
    browserName: 'chromium',
    headless: true,
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    acceptDownloads: false,
    serviceWorkers: 'block',
    // No recordHar, storageState, persisted auth or default developer API/UI origin.
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 720 } } },
    { name: 'mobile', use: { viewport: { width: 320, height: 720 } } },
  ],
});
