# T006 / T008 integration completion

Recorded: 2026-10-26. Owner: Lead/Architect. Local verification: PASS.

The human authorized T006 finalization, immediate non-fast-forward merges of Frontend and
QA into `001-appointment-scheduling`, completion documentation, and a non-force push of that
branch after local checks. GitHub-hosted results were explicitly not a prerequisite to the
first push. This scope excludes Backend T007 integration, further tasks, main and deployment.

## Source identities and scope

| Source | Commit |
| --- | --- |
| Shared starting baseline | `192a06d5fda29e3a01bac3ff0e8c026ce29c26de` |
| T008 / Frontend | `ee8be30add6255be80f3a996f48d967fbba9ad86` |
| T006 / QA | `c3257ad2fd9fe90c7d5d57354880f717b5087a1d` |
| Frontend merge | `ed671c5c31d96ed323607a96d21c1ce04cbe5eba` |
| QA merge / tested Lead tree | `1781e5afd45e02d2195679232d0402e9e597dfd7` |

Both component commits have the exact shared parent above and remain in Lead ancestry.
The merges introduce only six QA-owned `.github/` files and Frontend's Dockerfile and
`.dockerignore`. No squash, rebase, extra integration worktree or Backend merge was used.
Backend's branch HEAD, dirty-file inventory and both uncommitted T007 file hashes were
checked before and after verification and preserved. The final progress commit changes
only this record and the shared task list.

The `.github/README.md` handoff describes QA's pre-commit review and local checks;
its historical uncommitted/not-yet-pushed status is superseded by this completion record.
Earlier T001-only/first-batch authorization notes also remain historical records.

## Post-merge checks

All four lanes ran from repository root on the tested Lead commit using Python 3.12.12,
Node 22.22.0 and npm 10.9.4. Backend and QA used separate fresh virtual environments and
hash-locked installs. Contract and Frontend lanes ran serially to avoid shared npm writes.
Every command below exited 0 unless its expected negative outcome is stated.

| Command | Observed result |
| --- | --- |
| `python .github/ci/checks.py contract` | Locked contracts/Frontend installs and audits; `bash scripts/check-contract.sh --self-test`; TypeSpec/OpenAPI/types reproducible; 18 operations, 71 schema fixtures, 20 negative guards |
| `python .github/ci/checks.py backend` | Locked install and pip check; Ruff, format, mypy; 7 pytest cases; packaged timezone source check |
| `python .github/ci/checks.py frontend` | Locked install/audit; typecheck; production build; 54 Playwright cases |
| `python .github/ci/checks.py qa` | Independent locked Python/npm installs and audits; Ruff/format; 80 Python, 4 browser and 23 CI policy regression cases; TypeScript check |
| `docker build --platform linux/arm64 --build-arg VITE_API_BASE_URL=http://127.0.0.1:48123 -t slotbook-frontend:t006-t008-lead-1781e5a frontend` | Integrated Dockerfile builds; build/config/static-server regression layers reused the reviewed unchanged cache |
| Disposable Frontend container smoke, `docker exec` health probe and Chromium serving assertions | Nonroot `1000:1000`, read-only root, dropped capabilities, loopback dynamically allocated port; healthy; HTML/JS/CSS/HEAD/SPA and 400/404/405 paths pass |
| Same image with a different startup `VITE_API_BASE_URL` | Expected exit 1 with fixed rebuild-required diagnostic; no false startup success |
| Frozen trio comparison, ownership/ancestry checks, task preservation and Git whitespace checks | PASS |

All collected mandatory cases executed without failures or skips. The 168 tooling/scaffold
and CI regression cases are not the 77 approved product acceptance scenarios. The latter
remain future implementation requirements. All three npm projects' audit gates passed;
this does not imply container OS packages are vulnerability-free.

Backend tzdata: 2026.5 / IANA 2026e via empty `PYTHONTZPATH`. Both browser toolchains:
Playwright 1.64.1, Chromium 156.0.8078.4, revision 1248. Image runtime: Node 22.23.4;
build tooling: Node 22.22.0 / npm 10.9.4. Container verification covers linux/arm64 only.
T022 still must supply the build-time browser-reachable API origin and remove stale
development bind mounts. This does not exercise Compose, PostgreSQL or full application lifecycle.

## Sanitized evidence and frozen API

The four ignored local reports share source SHA-256
`077e238998cb5f8b066448d3f43f2b8a6297e73fbe1426ff8c766261b249bba8`
and the exact tested Lead commit. Their lane-specific candidate fingerprints are intentionally
different. Raw streams, fixture values and browser working files remain private outside Git.

| Local report under `test-results/` | SHA-256 |
| --- | --- |
| `ci-contract-3e3d235bae9d6889/verification.json` | `b4e092209382ddb2f4f7b4f2f4e82110a9ac4d86d30e21c0746c6571ca832ed2` |
| `ci-backend-0c874ad3d673b29b/verification.json` | `f69545a4eaa238aa87b6b47a50037ea9531d650e3e2886fc795d26cb7cf293ec` |
| `ci-frontend-38317cbc0f90315b/verification.json` | `d0de436a0c36eb03293d420cf4a3463d386e9e0104723987b1a10bd6c3418f2f` |
| `ci-qa-42cbb2dba1607940/verification.json` | `1260dd0090c37e9e4315ff6f598882a27d8f630a6bd9babce496a0e43851673d` |

The new build's runtime manifest is identical to the reviewed T008 scan target:
`sha256:486a33a6f3da194f19757b18814bb500d17946d15ead6043e9665655466c1432`;
runtime config `sha256:511b9264e055de2e4535bca973306050b04c25eba0e23d104d2a841ced1226af`.
The newly emitted image index is
`sha256:22acadb577d806e31b2f4f35e01e344b83dd09afaad2be06a332acd89615371f`;
the attestation/index identity differs from the prior build, while the runtime is unchanged.

Canonical TypeSpec, generated OpenAPI and generated TypeScript remain byte-for-byte equal
to frozen API v1 at `adc0b83a4408493ac44d3a7571dfd3d25a758679`. No application dependency,
contract, specification, amendment or requirements checklist changed during this integration.

## Development-image risk and production boundary

The prior independent Trivy 0.76.1 scan of this unchanged T008 runtime reported **229 package
findings**: 1 critical, 56 high, 87 medium, 83 low and 2 unknown (100 unique advisory IDs).
This is a recorded scan snapshot, not a fresh scan or a claim of exploitability for every match.
Its report SHA-256 is `092a641252853011bd6634bcf56bae3c0d849834d16fdd8b77fc9020e93a74ed`.
The critical match was CVE-2023-45853 against Debian `zlib1g`, marked `will_not_fix` by the
scan's vendor data; no formal risk acceptance or patched status is inferred from that label.
The snapshot also identified tzdata DLA-4854-1, installed `2026c-0+deb12u1`, with fixed
`2026e-0+deb12u1`. Other inherited Debian findings remain disclosed without blanket dismissal.

**This development image is not vulnerability-free.** Remediation or explicit documented risk
acceptance, supported by deployment-time verification, is required before production deployment.
The human explicitly authorized current development integration despite those findings.
Backend Docker security work is a separate open T007 review and does not block T006/T008.

## Completion and next gates

T006 and T008 are complete after passing local acceptance and integrated regression checks.
Seven of 92 tasks are checked; 85 remain unchecked, including T007. T007's existing
dependency/base/native-library security disposition remains open; no waiver is implied.
T-02 remains provisional and T-03 conditional. T024 and T034 remain uncompleted gates.

The first push will exercise the GitHub-hosted workflow; its run must be checked for the
exact pushed revision. Local results do not claim Ubuntu-hosted execution. Any hosted failure
must be reported or corrected within the authorized CI/integration scope; none is silently waived.
