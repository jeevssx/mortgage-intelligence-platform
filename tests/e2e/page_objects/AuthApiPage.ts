import { APIRequestContext } from "@playwright/test";

/**
 * "Page object" for the login flow — there's no UI, so this models the API interaction the same
 * way a real page object models a form: one class, one responsibility, callers never build the
 * request body or parse the response themselves.
 */
export class AuthApiPage {
  constructor(private readonly request: APIRequestContext, private readonly baseUrl: string) {}

  async login(username: string, password: string): Promise<{ status: number; accessToken?: string; roles?: string[] }> {
    const response = await this.request.post(`${this.baseUrl}/api/v1/auth/login`, {
      data: { username, password },
    });
    const status = response.status();
    if (status !== 200) {
      return { status };
    }
    const body = await response.json();
    return { status, accessToken: body.accessToken, roles: body.roles };
  }
}
