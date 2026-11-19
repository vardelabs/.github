# Bundle Secret Scan

A composite action that fails a job when a site's client-served output holds a provider secret. It runs two checks:

- **Name check:** a tracked code or config file in the checkout (prose files ending in `.md`, `.mdx`, `.rst` or `.txt` are skipped), or the job environment, names a secret under a public env prefix (`VITE_`, `NEXT_PUBLIC_`, `PUBLIC_`, `REACT_APP_`, `EXPO_PUBLIC_`). A name is secret when one of its `_` segments is `SECRET`, `TOKEN`, `PASSWORD`, `PASSWD` or `PRIVATE`, or when it ends in `API_KEY`. Bundlers inline these prefixes, so such a value ships to every visitor.
- **Output scan:** gitleaks, pinned by version and checksum, scans every served file except media (images, fonts, audio, video, PDF) with the default gitleaks rules plus the rules in `bundle-secrets.toml`. The `generic-api-key` rule is off, because minified code trips it. The default config also skips paths by name, such as `node_modules/` and `bootstrap*.js`, so `scan_served_output.py` copies each file to a neutral name before the scan and maps findings back to the served path.

Output is fully redacted, and the gitleaks report stays in a temp dir that is deleted after the scan, so the action is safe in a public repo's logs.

## Use

Build first, then point `path` at the directory the site serves. A static repo with no build points `path` at its served directory as committed.

```yaml
name: Bundle Secret Scan
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  bundle-secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955 # v4.3.0
      - run: npm ci && npm run build
      - uses: vardelabs/.github/bundle-secret-scan@<commit-sha>
        with:
          path: dist
```

Pin the action to a commit SHA. Run the build with the same public env vars as the production build, so the scan sees what ships.

## Inputs

- `path` (required): the served directory.
- `source-path`: the checkout the name check reads. Default `.`.
- `allow-names`: publishable names the name check lets through, comma- or newline-separated. Use it for an identifier meant to be public whose name still looks secret, such as `NEXT_PUBLIC_POSTHOG_API_KEY`.

## Gating a Deploy

The job blocks a merge only when it is a required status check on the branch. A host that builds outside Actions, such as Cloudflare Pages, deploys whatever merges. So make the check required before relying on it.

## Tests

`.github/workflows/bundle-secret-scan-test.yml` builds the Vite fixture in `test/fixture` three ways. A clean build must pass. A build with a generated fake key under `VITE_` must fail, once per key kind. A repo that names a secret under `VITE_` must fail the name check, and must pass when the name is allowed. `test/make_canary.py` generates the fake keys during the job, because a committed key-shaped literal trips push protection.
