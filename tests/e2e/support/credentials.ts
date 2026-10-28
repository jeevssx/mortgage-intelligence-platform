export interface Credentials {
  username: string;
  password: string;
}

const ROLE_ENV_PREFIX: Record<string, string> = {
  underwriter: "UNDERWRITER",
  servicing: "SERVICING",
  support: "SUPPORT",
  admin: "ADMIN",
};

export function credentialsFor(role: string): Credentials {
  const prefix = ROLE_ENV_PREFIX[role];
  if (!prefix) {
    throw new Error(`Unknown role "${role}" — add it to ROLE_ENV_PREFIX in support/credentials.ts`);
  }
  const username = process.env[`${prefix}_USERNAME`];
  const password = process.env[`${prefix}_PASSWORD`];
  if (!username || !password) {
    throw new Error(`Missing ${prefix}_USERNAME/${prefix}_PASSWORD — copy .env.example to .env`);
  }
  return { username, password };
}
