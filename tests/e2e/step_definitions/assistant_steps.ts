import { When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { World } from "../support/world";

When("the user asks the assistant {string}", async function (this: World, question: string) {
  const token = this.tokens["underwriter"] ?? Object.values(this.tokens)[0];
  this.lastResponse = await this.assistant.ask(token, question);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});

Then("the assistant's citations should not be empty", async function (this: World) {
  const body = this.lastBody as { citations?: unknown[] };
  expect(body.citations?.length).toBeGreaterThan(0);
});

Then("the assistant's citations should be empty", async function (this: World) {
  const body = this.lastBody as { citations?: unknown[] };
  expect(body.citations?.length).toBe(0);
});

Then("requiresHumanApproval should be {word}", async function (this: World, expected: string) {
  const body = this.lastBody as { requiresHumanApproval?: boolean };
  expect(body.requiresHumanApproval).toBe(expected === "true");
});
