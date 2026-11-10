# mortgage-api-consumer

TypeScript demo client for `mortgage-service` (8080) and `servicing-service` (8081), built for M6
task 6.4 ("secure API consumer"). Shows a login → Bearer token → authenticated `GET` flow with
automatic re-login on an expired/invalidated token.

## Run

Requires both Java services running against the seeded dev database
([database/README.md](../../database/README.md)) with `JWT_SECRET` set identically on both (see
their `.env.example` files).

```bash
cd clients/mortgage-api-consumer
npm install
cp .env.example .env   # DEMO_PASSWORD is the dev-only seed password from database/README.md
npm run demo
```

Expected output: login confirmation with roles, the `MTG-1001` mortgage record, its servicing
history, then a forced token invalidation followed by a successful re-login and a second
successful call.

## Files

```text
src/
├── auth.ts            AuthClient: login, in-memory token cache, invalidate()
├── mortgageClient.ts   MortgageClient: authenticated GETs, one retry after a 401
└── index.ts            demo script
```

## Design notes

- The token lives only in memory for the process lifetime — never written to disk, never logged.
- `AuthClient.ensureToken()` proactively re-logs-in 5 seconds before expiry; `MortgageClient`
  additionally catches a reactive `401` and retries once after invalidating the cache. There is
  no refresh-token endpoint yet (M6 scope), so both paths end in a full re-login with the
  original credentials.
- Base URLs and credentials come from environment variables (`.env`, git-ignored) — never commit
  real values. `.env.example` documents the dev-only seed password.
