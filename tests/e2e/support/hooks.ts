import "dotenv/config";
import { Before, After } from "@cucumber/cucumber";
import { request } from "@playwright/test";
import { AssistantApiPage } from "../page_objects/AssistantApiPage";
import { AuthApiPage } from "../page_objects/AuthApiPage";
import { MortgageApiPage } from "../page_objects/MortgageApiPage";
import { ServicingApiPage } from "../page_objects/ServicingApiPage";
import { World } from "./world";

const MORTGAGE_API_BASE = process.env.MORTGAGE_API_BASE ?? "http://localhost:8080";
const SERVICING_API_BASE = process.env.SERVICING_API_BASE ?? "http://localhost:8081";
const AI_ASSISTANT_BASE = process.env.AI_ASSISTANT_BASE ?? "http://localhost:8001";

Before(async function (this: World) {
  this.request = await request.newContext();
  this.auth = new AuthApiPage(this.request, MORTGAGE_API_BASE);
  this.mortgage = new MortgageApiPage(this.request, MORTGAGE_API_BASE);
  this.servicing = new ServicingApiPage(this.request, SERVICING_API_BASE);
  this.assistant = new AssistantApiPage(this.request, AI_ASSISTANT_BASE);
});

After(async function (this: World) {
  await this.request.dispose();
});
