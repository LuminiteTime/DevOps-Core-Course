import { defineWorkersConfig } from "@cloudflare/vitest-pool-workers/config";

export default defineWorkersConfig({
	test: {
		poolOptions: {
			workers: {
				wrangler: { configPath: "./wrangler.jsonc" },
				miniflare: {
					bindings: {
						ADMIN_EMAIL: "ops@example.com",
						API_TOKEN: "super-secret-token",
					},
				},
			},
		},
	},
});
