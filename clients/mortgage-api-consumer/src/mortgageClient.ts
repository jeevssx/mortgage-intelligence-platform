import { AuthClient } from "./auth";

export interface MortgageResponse {
  mortgageExternalId: string;
  borrowerExternalId: string;
  status: string;
  originalAmount: number;
  outstandingBalance: number;
  originationDate: string;
}

export interface ServicingHistoryResponse {
  mortgageExternalId: string;
  events: Array<{ eventTime: string; eventType: string; description?: string }>;
}

/**
 * Wraps mortgage-service and servicing-service calls with Authorization: Bearer <jwt>.
 * On a 401, invalidates the cached token and retries exactly once (re-login flow, M6 task 6.4) —
 * it does not retry indefinitely, so a genuinely bad credential still surfaces as an error.
 */
export class MortgageClient {
  constructor(
    private readonly mortgageApiBase: string,
    private readonly servicingApiBase: string,
    private readonly auth: AuthClient
  ) {}

  async getMortgage(mortgageExternalId: string): Promise<MortgageResponse> {
    return this.getWithAuth<MortgageResponse>(`${this.mortgageApiBase}/api/v1/mortgages/${mortgageExternalId}`);
  }

  async getServicingHistory(mortgageExternalId: string): Promise<ServicingHistoryResponse> {
    return this.getWithAuth<ServicingHistoryResponse>(
      `${this.servicingApiBase}/api/v1/mortgages/${mortgageExternalId}/servicing-history`
    );
  }

  private async getWithAuth<T>(url: string, attempt = 1): Promise<T> {
    const token = await this.auth.ensureToken();
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401 && attempt === 1) {
      this.auth.invalidate();
      return this.getWithAuth<T>(url, attempt + 1);
    }
    if (!response.ok) {
      throw new Error(`Request to ${url} failed: HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  }
}
