import { APIRequestContext, APIResponse } from "@playwright/test";

export class AssistantApiPage {
  constructor(private readonly request: APIRequestContext, private readonly baseUrl: string) {}

  // docker-compose sets JWT_SECRET for ai-assistant (shared with mortgage-service/
  // servicing-service), so /ask requires the same Bearer token those services issue.
  async ask(token: string, question: string): Promise<APIResponse> {
    return this.request.post(`${this.baseUrl}/api/v1/assistant/ask`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { question },
    });
  }
}
