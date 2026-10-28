import { When } from "@cucumber/cucumber";
import { World } from "../support/world";

When("an unauthenticated user requests mortgage {string}", async function (this: World, mortgageId: string) {
  this.lastResponse = await this.mortgage.getMortgage("", mortgageId);
  this.lastBody = await this.lastResponse.json().catch(() => ({}));
});
