import { Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { World } from "../support/world";

Then("the response status should be {int}", async function (this: World, expected: number) {
  expect(this.lastResponse!.status()).toBe(expected);
});

Then("the error code should be {string}", async function (this: World, expected: string) {
  const body = this.lastBody as { code?: string };
  expect(body.code).toBe(expected);
});
