import { setWorldConstructor, World as CucumberWorld, IWorldOptions } from "@cucumber/cucumber";
import { APIRequestContext, APIResponse } from "@playwright/test";
import { AssistantApiPage } from "../page_objects/AssistantApiPage";
import { AuthApiPage } from "../page_objects/AuthApiPage";
import { MortgageApiPage } from "../page_objects/MortgageApiPage";
import { ServicingApiPage } from "../page_objects/ServicingApiPage";

/** Shared state across steps within one scenario — tokens, the last response, generated IDs. */
export class World extends CucumberWorld {
  request!: APIRequestContext;
  auth!: AuthApiPage;
  mortgage!: MortgageApiPage;
  servicing!: ServicingApiPage;
  assistant!: AssistantApiPage;

  tokens: Record<string, string> = {};
  lastResponse?: APIResponse;
  lastBody?: unknown;
  generatedMortgageId?: string;
  generatedBorrowerId?: string;
  balanceBeforePayment?: number;

  constructor(options: IWorldOptions) {
    super(options);
  }
}

setWorldConstructor(World);
