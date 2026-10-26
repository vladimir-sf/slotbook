import { expect, test } from '@playwright/test';
import { createHash } from 'node:crypto';
import { chmodSync, mkdtempSync, realpathSync, symlinkSync, unlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

test.beforeEach(async ({}, info) => {
  const id = createHash('sha256').update(info.project.name + '/' + info.title).digest('hex');
  info.annotations.push(
    { type: 'evidence_id', description: 'QA-' + id },
    { type: 'candidate_sha256', description: process.env.SLOTBOOK_CANDIDATE_SHA256! },
    { type: 'associations', description: 'T004' },
  );
});

// Offline tooling assertion only; this is not evidence of any SlotBook product journey.
test('T004 Chromium fixture renders literal content at the assigned viewport', async ({ page }) => {
  await page.setContent('<main><p>QA synthetic fixture</p></main>');
  await expect(page.getByRole('main')).toHaveText('QA synthetic fixture');
  expect(await page.evaluate(() => window.innerWidth)).toBe(test.info().project.use.viewport?.width);
});

test('T004 browser report guards reject redirects before collection', async () => {
  // All rejection probes use synthetic targets in protected temporary storage, no browser/API.
  const probe = realpathSync(mkdtempSync(path.join(tmpdir(), 'slotbook-t004-probe-')));
  chmodSync(probe, 0o700);
  const cli = path.join(__dirname, 'node_modules/playwright/cli.js');
  const config = path.join(__dirname, 'playwright.config.ts');
  for (const override of ['PLAYWRIGHT_JUNIT_OUTPUT_FILE', 'PLAYWRIGHT_JUNIT_OUTPUT_DIR', 'PLAYWRIGHT_JUNIT_OUTPUT_NAME']) {
    const result = spawnSync(process.execPath, [cli, 'test', '-c', config, '--list'], {
      env: { ...process.env, SLOTBOOK_QA_PRIVATE_DIR: probe, [override]: path.join(probe, 'redirected') },
      encoding: 'utf8',
    });
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain('qa_guard:report_override_forbidden');
  }
  symlinkSync(path.join(probe, 'redirected.xml'), path.join(probe, 'e2e.xml'));
  const reportLink = spawnSync(process.execPath, [cli, 'test', '-c', config, '--list'], {
    env: { ...process.env, SLOTBOOK_QA_PRIVATE_DIR: probe }, encoding: 'utf8',
  });
  expect(reportLink.status).not.toBe(0);
  expect(reportLink.stderr).toContain('qa_guard:unsafe_private_output');
  unlinkSync(path.join(probe, 'e2e.xml'));
  symlinkSync(probe, path.join(probe, 'browser-work'), 'dir');
  const workLink = spawnSync(process.execPath, [cli, 'test', '-c', config, '--list'], {
    env: { ...process.env, SLOTBOOK_QA_PRIVATE_DIR: probe }, encoding: 'utf8',
  });
  expect(workLink.status).not.toBe(0);
  expect(workLink.stderr).toContain('qa_guard:unsafe_private_output');
});
