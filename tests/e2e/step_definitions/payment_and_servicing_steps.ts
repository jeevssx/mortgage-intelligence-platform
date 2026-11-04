import { When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { World } from "../support/world";

When("the user posts a payment of {string} on mortgage {string}", async function (this: World, amount: string, mortgageId: string) {
  const role = this.tokens["servicing"] ? "servicing" : this.tokens["support"] ? "support" : this.tokens["admin"] ? "admin" : "underwriter";
  const token = this.tokens[role];

  // Record the balance before, when we can (needed for the "decreased by" assertion) — a failed
  // auth/validation scenario may not have a balance to read, which is fine.
  const before = await this.mortgage.getMortgage(token, mortgageId);
  if (before.ok()) {
    const body = await before.json();
    this.balanceBeforePayment = body.outstandingBalance;
  }

  const payment = {
    dueDate: "2026-04-01",
    paidDate: "2026-04-02",
    amount: Number(amount),
    status: "POSTED",
  };
  this.lastResponse = await this.mortgage.postPayment(token, mortgageId, payment);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

Then("the outstanding balance should have decreased by {string}", async function (this: World, amount: string) {
  const body = this.lastBody as { outstandingBalanceAfter?: number };
  expect(this.balanceBeforePayment).toBeDefined();
  expect(body.outstandingBalanceAfter).toBeCloseTo(this.balanceBeforePayment! - Number(amount), 2);
});

When("the user requests servicing history for mortgage {string}", async function (this: World, mortgageId: string) {
  const token = this.tokens["servicing"] ?? this.tokens["admin"];
  this.lastResponse = await this.servicing.getServicingHistory(token, mortgageId);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

Then("the servicing history should include a {string} event", async function (this: World, eventType: string) {
  const body = this.lastBody as { events?: Array<{ eventType: string }> };
  expect(body.events?.some((e) => e.eventType === eventType)).toBe(true);
});
