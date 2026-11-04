import { When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { World } from "../support/world";

When("the user requests delinquency status for mortgage {string}", async function (this: World, mortgageId: string) {
  const token = this.tokens["servicing"] ?? this.tokens["admin"];
  this.lastResponse = await this.servicing.getDelinquency(token, mortgageId);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

Then("the delinquency status should be {string}", async function (this: World, expected: string) {
  const body = this.lastBody as { status?: string };
  expect(body.status).toBe(expected);
});

Then("the days past due should be at least {int}", async function (this: World, minimum: number) {
  const body = this.lastBody as { daysPastDue?: number };
  expect(body.daysPastDue).toBeGreaterThanOrEqual(minimum);
});

Then("the severity should be {string}", async function (this: World, expected: string) {
  const body = this.lastBody as { severity?: string };
  expect(body.severity).toBe(expected);
});
