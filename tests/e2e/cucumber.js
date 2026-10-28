module.exports = {
  default: {
    requireModule: ["ts-node/register"],
    require: ["support/**/*.ts", "step_definitions/**/*.ts"],
    paths: ["features/**/*.feature"],
    format: ["summary", "progress-bar"],
    retry: 1,
    retryTagFilter: "@flaky",
  },
};
