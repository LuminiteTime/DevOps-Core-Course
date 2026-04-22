import {
	env,
	createExecutionContext,
	waitOnExecutionContext,
	SELF,
} from "cloudflare:test";
import { describe, it, expect } from "vitest";
import worker from "../src/index";

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

describe("edge-api worker", () => {
	it("returns health metadata", async () => {
		const request = new IncomingRequest("http://example.com/health");
		const ctx = createExecutionContext();
		const response = await worker.fetch(request, env, ctx);
		await waitOnExecutionContext(ctx);
		expect(response.status).toBe(200);
		expect(await response.json()).toMatchObject({
			status: "ok",
			service: "edge-api",
			environment: "production",
		});
	});

	it("returns edge metadata from request.cf", async () => {
		const request = new IncomingRequest("http://example.com/edge", {
			cf: {
				colo: "SVO",
				country: "RU",
				city: "Moscow",
				asn: 12389,
				httpProtocol: "HTTP/2",
				tlsVersion: "TLSv1.3",
			},
		});
		const ctx = createExecutionContext();
		const response = await worker.fetch(request, env, ctx);
		await waitOnExecutionContext(ctx);
		expect(await response.json()).toMatchObject({
			colo: "SVO",
			country: "RU",
			city: "Moscow",
			asn: 12389,
			httpProtocol: "HTTP/2",
			tlsVersion: "TLSv1.3",
		});
	});

	it("persists the counter through the KV binding", async () => {
		const first = await SELF.fetch("https://example.com/counter");
		const second = await SELF.fetch("https://example.com/counter");
		const peek = await SELF.fetch("https://example.com/counter?peek=1");

		expect(await first.json()).toMatchObject({ visits: 1, persisted: true });
		expect(await second.json()).toMatchObject({ visits: 2, persisted: true });
		expect(await peek.json()).toMatchObject({ visits: 2, peekOnly: true });
	});

	it("exposes deployment metadata and redacted secret info", async () => {
		const response = await SELF.fetch("https://example.com/meta");
		const body = await response.json();

		expect(body).toMatchObject({
			app: "edge-api",
			course: "devops-core-course",
			version: "1.1.0",
			secrets: {
				adminEmailConfigured: true,
				apiTokenConfigured: true,
			},
		});
	});
});
