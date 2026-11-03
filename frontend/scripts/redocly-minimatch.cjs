// Redocly 1.x calls the CommonJS export directly. Minimatch 11.0.1 fixes
// GHSA-g3hv-75wg-m249 and exposes that function as a named export instead.
// Adapt only Redocly's resolved module in the contract tooling processes.
const { createRequire } = require("node:module");

const redoclyRequire = createRequire(require.resolve("@redocly/openapi-core"));
const minimatchPath = redoclyRequire.resolve("minimatch");
const patched = redoclyRequire(minimatchPath);

if (typeof patched.minimatch !== "function") {
  throw new TypeError("The patched minimatch module must expose minimatch()");
}

require.cache[minimatchPath].exports = Object.assign(
  (...args) => patched.minimatch(...args),
  patched,
);
