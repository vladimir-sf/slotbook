import { defineConfig } from "@playwright/test";
import { mkdtempSync, realpathSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

// QA may supply an existing, owner-only directory unique to this run. Raw JUnit
// and artifacts must stay outside the checkout until QA sanitizes them.
const checkout = realpathSync(resolve(dirname(fileURLToPath(import.meta.url)), ".."));
export function privateReportDirectory(supplied?: string): string {
  const directory = supplied ?? mkdtempSync(resolve(tmpdir(), "slotbook-frontend-"));
  if (!isAbsolute(directory)) {
    throw new Error("T003_REPORT_DIRECTORY_OUTSIDE_CHECKOUT_REQUIRED");
  }
  const canonical = realpathSync(directory);
  const fromCheckout = relative(checkout, canonical);
  if (!fromCheckout.startsWith(`..${sep}`) && !isAbsolute(fromCheckout)) {
    throw new Error("T003_REPORT_DIRECTORY_OUTSIDE_CHECKOUT_REQUIRED");
  }
  const info = statSync(canonical);
  if (!info.isDirectory() || (info.mode & 0o077) !== 0 || (process.getuid && info.uid !== process.getuid())) {
    throw new Error("T003_OWNER_ONLY_REPORT_DIRECTORY_REQUIRED");
  }
  return canonical;
}

const reportDirectory = privateReportDirectory(process.env.SLOTBOOK_FRONTEND_REPORT_DIR);

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  forbidOnly: true,
  retries: 0,
  workers: 1,
  outputDir: resolve(reportDirectory, "artifacts"),
  reporter: [
    ["list"],
    ["junit", { outputFile: resolve(reportDirectory, "junit.xml"), includeProjectInTestName: true, stripANSIControlSequences: true }],
  ],
  use: {
    browserName: "chromium",
    baseURL: "http://127.0.0.1:4173",
    timezoneId: "Europe/Vienna",
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    stdout: "ignore",
    stderr: "ignore",
  },
});
