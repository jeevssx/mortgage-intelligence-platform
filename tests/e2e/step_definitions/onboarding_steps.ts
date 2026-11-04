import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { credentialsFor } from "../support/credentials";
import { getCachedToken, setCachedToken } from "../support/token_cache";
import { World } from "../support/world";

function randomSuffix(): string {
  return String(9000 + Math.floor(Math.random() * 900)); // MTG-9000..9899 — avoids seed/demo IDs
}

Given("the user {string} is authenticated", async function (this: World, role: string) {
  const cached = getCachedToken(role);
  if (cached) {
    this.tokens[role] = cached;
    return;
  }
  const { username, password } = credentialsFor(role);
  const result = await this.auth.login(username, password);
  expect(result.status).toBe(200);
  this.tokens[role] = result.accessToken!;
  setCachedToken(role, result.accessToken!);
});

When("the user creates a new borrower", async function (this: World) {
  const suffix = randomSuffix().slice(-3);
  const borrower = {
    borrowerExternalId: `BOR-${suffix}`,
    firstName: "E2E",
    lastName: "TestBorrower",
    email: `e2e-${suffix}@example.test`,
  };
  this.generatedMortgageId = undefined;
  this.generatedBorrowerId = borrower.borrowerExternalId;
  this.lastResponse = await this.mortgage.createBorrower(this.tokens["underwriter"], borrower);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

When("the user creates a new mortgage for that borrower with an approved loan", async function (this: World) {
  const mortgageId = `MTG-${randomSuffix()}`;
  this.generatedMortgageId = mortgageId;
  const mortgage = {
    mortgageExternalId: mortgageId,
    borrowerExternalId: this.generatedBorrowerId,
    originalAmount: 250000.0,
    outstandingBalance: 250000.0,
    originationDate: "2026-01-01",
    loan: {
      loanExternalId: `LOAN-${randomSuffix()}`,
      interestRate: 0.0599,
      termMonths: 360,
      underwritingDecision: "APPROVED",
    },
  };
  this.lastResponse = await this.mortgage.createMortgage(this.tokens["underwriter"], mortgage);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

When("the user creates a mortgage for borrower {string} which does not exist", async function (this: World, borrowerId: string) {
  const mortgage = {
    mortgageExternalId: `MTG-${randomSuffix()}`,
    borrowerExternalId: borrowerId,
    originalAmount: 100000.0,
    outstandingBalance: 100000.0,
    originationDate: "2026-01-01",
  };
  this.lastResponse = await this.mortgage.createMortgage(this.tokens["underwriter"], mortgage);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

Then("the mortgage status should be {string}", async function (this: World, expected: string) {
  const body = this.lastBody as { status?: string };
  expect(body.status).toBe(expected);
});
