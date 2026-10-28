import { APIRequestContext, APIResponse } from "@playwright/test";

export class ServicingApiPage {
  constructor(private readonly request: APIRequestContext, private readonly baseUrl: string) {}

  private authHeader(token?: string): Record<string, string> {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async getServicingHistory(token: string, mortgageExternalId: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}/api/v1/mortgages/${mortgageExternalId}/servicing-history`, {
      headers: this.authHeader(token),
    });
  }

  async getDelinquency(token: string, mortgageExternalId: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}/api/v1/mortgages/${mortgageExternalId}/delinquency`, {
      headers: this.authHeader(token),
    });
  }
}
