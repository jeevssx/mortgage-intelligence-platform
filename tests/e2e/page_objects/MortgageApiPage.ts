import { APIRequestContext, APIResponse } from "@playwright/test";

export class MortgageApiPage {
  constructor(private readonly request: APIRequestContext, private readonly baseUrl: string) {}

  private authHeader(token?: string): Record<string, string> {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async createBorrower(token: string, borrower: Record<string, unknown>): Promise<APIResponse> {
    return this.request.post(`${this.baseUrl}/api/v1/borrowers`, {
      headers: this.authHeader(token),
      data: borrower,
    });
  }

  async getBorrower(token: string, borrowerExternalId: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}/api/v1/borrowers/${borrowerExternalId}`, {
      headers: this.authHeader(token),
    });
  }

  async createMortgage(token: string, mortgage: Record<string, unknown>): Promise<APIResponse> {
    return this.request.post(`${this.baseUrl}/api/v1/mortgages`, {
      headers: this.authHeader(token),
      data: mortgage,
    });
  }

  async getMortgage(token: string, mortgageExternalId: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}/api/v1/mortgages/${mortgageExternalId}`, {
      headers: this.authHeader(token),
    });
  }

  async postPayment(token: string, mortgageExternalId: string, payment: Record<string, unknown>): Promise<APIResponse> {
    return this.request.post(`${this.baseUrl}/api/v1/mortgages/${mortgageExternalId}/payments`, {
      headers: this.authHeader(token),
      data: payment,
    });
  }
}
