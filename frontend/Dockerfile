# T008 handoff (build context: frontend/):
#   docker build --build-arg VITE_API_BASE_URL=http://127.0.0.1:<QA_API_PORT> -t <image> frontend
#   docker run --read-only --cap-drop ALL --security-opt no-new-privileges \
#     -p 127.0.0.1:<QA_UI_PORT>:5173 <image>
# VITE_API_BASE_URL is a required public, canonical HTTP(S) origin with no trailing
# slash, path, query, fragment or credentials. Vite embeds it at BUILD time for
# import.meta.env.VITE_API_BASE_URL; the current scaffold makes no API calls yet.
# Changing the browser API origin requires rebuilding. A different startup value
# fails closed rather than silently serving an old origin. Use a browser-reachable
# origin, not a Compose service name. There is no API proxy or runtime config route.
# QA owns Compose build.args and host port allocation in T022. Existing development
# bind mounts must not shadow /app; this image serves built assets, without HMR.
# Default target: non-root static runtime on 0.0.0.0:5173, with GET / as health probe.
# Only dist/, the static server and public origin metadata enter the runtime stage.
# Build runs locked npm ci, npm run build and the embedded serving/config tests.
# Host typecheck/Playwright still use T003's commands and private report directory;
# tests/ and browsers are deliberately excluded from the image/build context.
# Playwright 1.64.1 locks Chromium 156.0.8078.4, revision 1248 (host browser tests).
# Build tooling stays on reviewed Node 22.22.0/npm 10.9.4. The shipped runtime uses
# Node 22.23.4 and omits unused npm, Corepack and Yarn after an independent scan.
# Both index digests were verified against the official registry on 2026-10-26.
# Verified arm64 build manifest: 5e22e6fb4448236070fdb260662e49fd58779876855baf95388534475c3dcd11.
# Verified arm64 runtime manifest: ceb43e5c219139035fb742900629e4abed89fe0997f7c03250c499e1f2710c9e.
# Acceptance is verified on linux/arm64 only; other platforms remain unverified.
FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94 AS build
WORKDIR /app
ENV TZ=UTC
RUN test "$(node --version)" = v22.22.0 && test "$(npm --version)" = 10.9.4
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . .

# A dependency-free static server keeps the runtime on a pinned Node 22 base.
# It serves only files under dist/, never requests to the backend API namespace,
# and never logs URLs, headers, bodies or exception values.
COPY <<'JS' /app/server.mjs
import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { realpathSync, readFileSync } from "node:fs";
import { extname, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";

export function validateApiOrigin(value) {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol) || url.origin !== value || url.username || url.password) throw new Error();
    return value;
  } catch {
    throw new Error("SLOTBOOK_API_ORIGIN_INVALID");
  }
}

export function validateRuntimeOrigin(value, baked) {
  if (value !== undefined && value !== baked) throw new Error("SLOTBOOK_API_ORIGIN_REBUILD_REQUIRED");
}

export function staticServer(directory) {
  const root = realpathSync(directory);
  const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2", ".wasm": "application/wasm" };
  return createServer({ requestTimeout: 15000, headersTimeout: 10000, maxHeaderSize: 8192 }, async (request, response) => {
    const send = (status, body, type = "text/plain; charset=utf-8") => {
      response.writeHead(status, { "Content-Type": type, "Content-Length": Buffer.byteLength(body), "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", ...(status === 405 ? { Allow: "GET, HEAD" } : {}) });
      response.end(request.method === "HEAD" ? undefined : body);
    };
    try {
      if (!["GET", "HEAD"].includes(request.method)) { request.resume(); return send(405, "Method not allowed\n"); }
      let pathname;
      try { pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname); }
      catch { return send(400, "Invalid request\n"); }
      if (pathname.includes("\0") || pathname.includes("\\")) return send(400, "Invalid request\n");
      if (pathname.split("/").some((part) => part.startsWith(".")) || pathname === "/api" || pathname.startsWith("/api/")) return send(404, "Not found\n");
      let filename = await realpath(resolve(root, `.${pathname === "/" ? "/index.html" : pathname}`)).catch(() => null);
      if (!filename && !extname(pathname) && !pathname.startsWith("/assets/") && request.headers.accept?.includes("text/html")) filename = await realpath(resolve(root, "index.html"));
      if (!filename || !filename.startsWith(root + sep) || !(await stat(filename)).isFile()) return send(404, "Not found\n");
      return send(200, await readFile(filename), types[extname(filename)] ?? "application/octet-stream");
    } catch { return send(500, "Service unavailable\n"); }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const baked = validateApiOrigin(JSON.parse(readFileSync(new URL("./api-origin.json", import.meta.url), "utf8")).origin);
    validateRuntimeOrigin(process.env.VITE_API_BASE_URL, baked);
    const server = staticServer(new URL("./dist/", import.meta.url));
    server.on("error", () => { console.error("SLOTBOOK_FRONTEND_START_FAILED"); process.exit(1); });
    server.listen(5173, "0.0.0.0");
    process.on("SIGTERM", () => server.close());
    process.on("SIGINT", () => server.close());
  } catch { console.error("SLOTBOOK_FRONTEND_CONFIG_INVALID_OR_REBUILD_REQUIRED"); process.exit(1); }
}
JS

ARG VITE_API_BASE_URL
RUN node --input-type=module <<'JS'
import { writeFileSync } from "node:fs";
import { validateApiOrigin } from "./server.mjs";
writeFileSync("api-origin.json", JSON.stringify({ origin: validateApiOrigin(process.env.VITE_API_BASE_URL) }) + "\n");
JS
RUN npm run build

# Durable regression tests live here to keep T008 within its two assigned paths.
# No fixtures or test control are added to the public app or final image.
RUN node --input-type=module <<'JS'
import assert from "node:assert/strict";
import { test } from "node:test";
import { once } from "node:events";
import { mkdtemp, readFile, writeFile, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { validateApiOrigin, validateRuntimeOrigin, staticServer } from "./server.mjs";

await test("T008 accepts canonical public origins and rejects invalid configuration", () => {
  for (const value of ["http://127.0.0.1:48123", "https://example.invalid", "http://[::1]:48123"]) assert.equal(validateApiOrigin(value), value);
  for (const value of [undefined, "", "/api", "file:///tmp/api", "http://user:synthetic@example.invalid", "http://example.invalid/", "http://example.invalid/api", "http://example.invalid?key=synthetic", "http://example.invalid#fragment"]) assert.throws(() => validateApiOrigin(value), /SLOTBOOK_API_ORIGIN_INVALID/);
  const origin = "http://127.0.0.1:48123";
  validateRuntimeOrigin(undefined, origin);
  validateRuntimeOrigin(origin, origin);
  assert.throws(() => validateRuntimeOrigin("http://127.0.0.1:48124", origin), /SLOTBOOK_API_ORIGIN_REBUILD_REQUIRED/);
});

await test("T008 serves built assets and handles errors without exposing private files", async () => {
  const server = staticServer("dist");
  const temporary = await mkdtemp(resolve(tmpdir(), "slotbook-static-"));
  try {
    await writeFile(resolve(temporary, "private.txt"), "synthetic-private-marker");
    await symlink(resolve(temporary, "private.txt"), "dist/outside.txt");
    server.listen(0, "127.0.0.1");
    await once(server, "listening");
    const base = `http://127.0.0.1:${server.address().port}`;
    const home = await fetch(base);
    const html = await home.text();
    assert.equal(home.status, 200);
    assert.match(home.headers.get("content-type"), /text\/html/);
    assert.equal(home.headers.get("cache-control"), "no-store");
    assert.equal(home.headers.get("x-content-type-options"), "nosniff");
    assert.equal(html, await readFile("dist/index.html", "utf8"));
    const script = html.match(/src="([^"]+\.js)"/)[1];
    const asset = await fetch(base + script);
    assert.equal(asset.status, 200);
    assert.match(asset.headers.get("content-type"), /javascript/);
    const head = await fetch(base, { method: "HEAD" });
    assert.equal(head.status, 200); assert.equal(await head.text(), "");
    const navigation = await fetch(base + "/synthetic-navigation", { headers: { Accept: "text/html" } });
    assert.equal(navigation.status, 200); assert.equal(await navigation.text(), html);
    for (const path of ["/package.json", "/server.mjs", "/api-origin.json", "/.env", "/assets/missing.js", "/api/activities", "/outside.txt", "/%2e%2e%2fpackage.json"]) {
      const result = await fetch(base + path, { headers: { Accept: "text/html" } });
      assert.equal(result.status, 404); assert.equal(await result.text(), "Not found\n");
    }
    assert.equal((await fetch(base + "/%FF")).status, 400);
    const post = await fetch(base, { method: "POST", body: "synthetic-body" });
    assert.equal(post.status, 405); assert.equal(post.headers.get("allow"), "GET, HEAD");
  } finally {
    await new Promise((done) => server.close(done));
    await rm("dist/outside.txt", { force: true });
    await rm(temporary, { recursive: true, force: true });
  }
});
JS

FROM node:22.23.4-bookworm-slim@sha256:de170b39439eb0e5a3444ad7d60b015614a381e10fecae2e30ec9e735122f38d AS runtime
ENV NODE_ENV=production TZ=UTC
WORKDIR /app
# Package managers are build tools, not dependencies of this static server.
# Remove their actual files; vulnerability findings are never filtered/ignored.
RUN rm -rf /usr/local/lib/node_modules /opt/yarn-v1.22.22 \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
      /usr/local/bin/yarn /usr/local/bin/yarnpkg /usr/local/bin/pnpm /usr/local/bin/pnpx \
    && node --input-type=module -e 'import assert from "node:assert/strict"; import {existsSync} from "node:fs"; assert.equal(process.version,"v22.23.4"); for(const p of ["/usr/local/lib/node_modules","/opt/yarn-v1.22.22"]) assert.equal(existsSync(p),false);'
COPY --from=build /app/dist ./dist
COPY --from=build /app/server.mjs /app/api-origin.json ./
USER 1000:1000
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e 'fetch("http://127.0.0.1:5173/").then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))'
ENTRYPOINT ["node"]
CMD ["/app/server.mjs"]
