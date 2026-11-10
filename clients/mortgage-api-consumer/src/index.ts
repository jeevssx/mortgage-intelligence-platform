import "dotenv/config";
import { AuthClient } from "./auth";
import { MortgageClient } from "./mortgageClient";

async function main(): Promise<void> {
  const mortgageApiBase = process.env.MORTGAGE_API_BASE ?? "http://localhost:8080";
  const servicingApiBase = process.env.SERVICING_API_BASE ?? "http://localhost:8081";
  const username = process.env.DEMO_USERNAME ?? "servicing@capstone.local";
  const password = process.env.DEMO_PASSWORD;
  const mortgageId = process.env.DEMO_MORTGAGE_ID ?? "MTG-1001";

  if (!password) {
    throw new Error("Set DEMO_PASSWORD (see .env.example) — never hardcode credentials in source.");
  }

  const auth = new AuthClient(mortgageApiBase, username, password);
  const client = new MortgageClient(mortgageApiBase, servicingApiBase, auth);

  console.log(`Logging in as ${username} ...`);
  const login = await auth.login();
  console.log(`Logged in. Roles: ${login.roles.join(", ")}. Token expires in ${login.expiresInSeconds}s.`);

  console.log(`\nGET mortgage ${mortgageId} ...`);
  const mortgage = await client.getMortgage(mortgageId);
  console.log(mortgage);

  console.log(`\nGET servicing history for ${mortgageId} ...`);
  const history = await client.getServicingHistory(mortgageId);
  console.log(history);

  // Demonstrate the re-login flow: force the cached token to look expired, then call again.
  console.log("\nForcing token invalidation to demonstrate automatic re-login ...");
  auth.invalidate();
  const mortgageAgain = await client.getMortgage(mortgageId);
  console.log(`Re-login succeeded; mortgage status is still ${mortgageAgain.status}.`);
}

main().catch((err) => {
  console.error("Demo failed:", err instanceof Error ? err.message : err);
  process.exitCode = 1;
});
