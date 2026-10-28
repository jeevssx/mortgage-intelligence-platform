/**
 * Minimal in-memory JWT auth client. No refresh-token endpoint exists yet (M6 scope — see
 * docs/security/security-controls.md), so "refresh" here means re-login with the same
 * credentials when the cached token is expired or the server returns 401.
 */

export interface LoginResponse {
  accessToken: string;
  expiresInSeconds: number;
  roles: string[];
}

export class AuthClient {
  private readonly baseUrl: string;
  private readonly username: string;
  private readonly password: string;

  private token: string | null = null;
  private expiresAt: number = 0; // epoch millis

  constructor(baseUrl: string, username: string, password: string) {
    this.baseUrl = baseUrl;
    this.username = username;
    this.password = password;
  }

  async login(): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: this.username, password: this.password }),
    });
    if (!response.ok) {
      throw new Error(`Login failed: HTTP ${response.status}`);
    }
    const body = (await response.json()) as LoginResponse;
    this.token = body.accessToken;
    this.expiresAt = Date.now() + body.expiresInSeconds * 1000;
    return body;
  }

  /** Returns a valid token, logging in (or re-logging in) first if necessary. Never logs the token itself. */
  async ensureToken(): Promise<string> {
    const expiringSoonMs = 5_000;
    if (!this.token || Date.now() > this.expiresAt - expiringSoonMs) {
      await this.login();
    }
    return this.token as string;
  }

  /** Forces the next ensureToken() call to re-login — used when a request comes back 401. */
  invalidate(): void {
    this.token = null;
    this.expiresAt = 0;
  }
}
