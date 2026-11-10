/**
 * Module-level (not per-scenario) token cache. mortgage-service rate-limits /auth/login to
 * 10 requests/60s per client IP (RateLimitFilter) — with 12 scenarios each logging in via a
 * Background step, the suite's own login traffic was tripping that limit before role-specific
 * scenarios even ran. Tokens don't depend on any particular scenario's request context, so one
 * login per role for the whole suite run is correct, not just a workaround.
 */
const tokens = new Map<string, string>();

export function getCachedToken(role: string): string | undefined {
  return tokens.get(role);
}

export function setCachedToken(role: string, token: string): void {
  tokens.set(role, token);
}
