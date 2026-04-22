type EdgeRequest = Request<unknown, IncomingRequestCfProperties>;

interface WorkerSecrets {
	ADMIN_EMAIL?: string;
	API_TOKEN?: string;
}

function json(data: unknown, init?: ResponseInit): Response {
	return Response.json(data, {
		headers: {
			"cache-control": "no-store",
		},
		...init,
	});
}

function maskEmail(email?: string): string | null {
	if (!email || !email.includes("@")) {
		return null;
	}

	const [local, domain] = email.split("@");
	const visiblePrefix = local.slice(0, 2) || "*";
	return `${visiblePrefix}***@${domain}`;
}

function describeSecrets(env: WorkerSecrets) {
	return {
		adminEmailConfigured: Boolean(env.ADMIN_EMAIL),
		adminEmailMasked: maskEmail(env.ADMIN_EMAIL),
		apiTokenConfigured: Boolean(env.API_TOKEN),
		apiTokenLength: env.API_TOKEN?.length ?? 0,
	};
}

async function readCounter(env: Env): Promise<number> {
	const raw = await env.SETTINGS.get("visits");
	return Number.parseInt(raw ?? "0", 10) || 0;
}

async function incrementCounter(env: Env): Promise<number> {
	const current = await readCounter(env);
	const next = current + 1;
	await env.SETTINGS.put("visits", String(next));
	return next;
}

function getEdgeMetadata(request: EdgeRequest) {
	return {
		colo: request.cf?.colo ?? null,
		country: request.cf?.country ?? null,
		city: request.cf?.city ?? null,
		asn: request.cf?.asn ?? null,
		httpProtocol: request.cf?.httpProtocol ?? null,
		tlsVersion: request.cf?.tlsVersion ?? null,
	};
}

export default {
	async fetch(request: EdgeRequest, env: Env): Promise<Response> {
		const url = new URL(request.url);
		const startedAt = new Date().toISOString();

		console.log("request", {
			path: url.pathname,
			method: request.method,
			colo: request.cf?.colo ?? "local",
			country: request.cf?.country ?? "local",
		});

		if (url.pathname === "/") {
			return json({
				app: env.APP_NAME,
				course: env.COURSE_NAME,
				environment: env.DEPLOYMENT_ENV,
				version: env.DEPLOYMENT_VERSION,
				message: "DevOps edge API is running on Cloudflare Workers.",
				routes: ["/", "/health", "/meta", "/edge", "/counter"],
			});
		}

		if (url.pathname === "/health") {
			return json({
				status: "ok",
				service: env.APP_NAME,
				environment: env.DEPLOYMENT_ENV,
				timestamp: startedAt,
			});
		}

		if (url.pathname === "/meta") {
			return json({
				app: env.APP_NAME,
				course: env.COURSE_NAME,
				environment: env.DEPLOYMENT_ENV,
				version: env.DEPLOYMENT_VERSION,
				deployedAt: env.DEPLOYED_AT,
				requestId: request.headers.get("cf-ray"),
				url: request.url,
				secrets: describeSecrets(env),
			});
		}

		if (url.pathname === "/edge") {
			return json({
				timestamp: startedAt,
				...getEdgeMetadata(request),
			});
		}

		if (url.pathname === "/counter") {
			const peekOnly = url.searchParams.get("peek") === "1";
			const visits = peekOnly ? await readCounter(env) : await incrementCounter(env);

			return json({
				key: "visits",
				visits,
				peekOnly,
				persisted: true,
			});
		}

		return json(
			{
				error: "Not Found",
				path: url.pathname,
			},
			{ status: 404 },
		);
	},
} satisfies ExportedHandler<Env>;
