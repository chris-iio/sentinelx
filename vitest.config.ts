import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["app/static/src/ts/**/*.test.ts", "tests/audit-gpt-routing.test.ts"],
    globals: true,
    typecheck: {
      tsconfig: "tsconfig.test.json",
    },
  },
});
