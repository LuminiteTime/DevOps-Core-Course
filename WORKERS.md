# Cloudflare Workers Deployment Report

## Deployment Summary

- Worker URL: `https://edge-api.luminais-devops-core.workers.dev`
- Worker project: `workers/edge-api`
- Runtime: Cloudflare Workers with Wrangler `4.84.1`
- Account email: `trifonov2812@gmail.com`
- Account ID: `22e56e51e9cafec1122526a7429dce9c`
- `workers.dev` subdomain: `luminais-devops-core.workers.dev`

### Implemented Routes

| Route | Purpose |
| --- | --- |
| `/` | General deployment information and route list |
| `/health` | Health check with service name, environment, and timestamp |
| `/meta` | Deployment metadata and redacted secret status |
| `/edge` | Cloudflare edge metadata from `request.cf` |
| `/counter` | Workers KV backed persistent counter |

### Configuration Summary

**Plaintext variables in `wrangler.jsonc`:**

| Variable | Value |
| --- | --- |
| `APP_NAME` | `edge-api` |
| `COURSE_NAME` | `devops-core-course` |
| `DEPLOYMENT_ENV` | `production` |
| `DEPLOYMENT_VERSION` | `1.1.0` |
| `DEPLOYED_AT` | `2026-04-22T08:41:00Z` |

Plaintext vars are suitable for non-sensitive configuration only because the values are committed to source control and visible in the deployed Worker configuration.

**Secrets configured with Wrangler:**

- `ADMIN_EMAIL`
- `API_TOKEN`

Secrets are exposed only through the `env` object. The `/meta` endpoint returns redacted indicators instead of raw secret values.

**Workers KV binding:**

| Binding | Namespace ID | Usage |
| --- | --- | --- |
| `SETTINGS` | `521855d07d544efdbebb06ca7517dbe5` | Stores the `visits` counter |

## Functional Verification

### Local Automated Tests

`npm test` in `workers/edge-api` passes after the final metadata version sync.

Covered behaviors:

- `/health` response
- `/edge` request metadata parsing
- `/counter` persistence with KV
- `/meta` deployment metadata and secret redaction

### Public Endpoint Evidence

Direct requests from the current network to `workers.dev` failed during TLS negotiation. Public verification was therefore performed through `r.jina.ai`, which successfully fetched the deployed Worker.

**Observed `/health` response:**

```json
{"status":"ok","service":"edge-api","environment":"production","timestamp":"2026-04-22T08:39:38.019Z"}
```

**Observed `/edge` response:**

```json
{"timestamp":"2026-04-22T08:39:48.172Z","colo":"IAD","country":"US","city":"North Charleston","asn":396982,"httpProtocol":"HTTP/1.1","tlsVersion":""}
```

**Observed `/meta` response:**

```json
{"app":"edge-api","course":"devops-core-course","environment":"production","version":"1.1.0","deployedAt":"2026-04-22T08:41:00Z","requestId":"9f03872b3fdcd46d","url":"http://edge-api.luminais-devops-core.workers.dev/meta?nocache=20260422-final","secrets":{"adminEmailConfigured":true,"adminEmailMasked":"ed***@example.com","apiTokenConfigured":true,"apiTokenLength":23}}
```

### Persistence Verification

Workers KV persistence was verified through repeated `/counter` requests:

- first request returned `{"visits":1,"persisted":true}`
- second request returned `{"visits":2,"persisted":true}`
- `?peek=1` returned `{"visits":2,"peekOnly":true,"persisted":true}`

The value remained available after redeploys because the counter is stored in Workers KV, not in ephemeral runtime memory.

## Edge Behavior and Routing

Cloudflare Workers runs the script on Cloudflare's edge network instead of deploying separate VM instances into manually chosen regions. Requests are routed to a nearby Cloudflare location automatically, which is why the `/edge` endpoint can expose metadata such as `colo`, `country`, `city`, `asn`, and `httpProtocol` without any explicit multi-region deployment step.

### `workers.dev` vs Routes vs Custom Domains

| Option | Meaning | Used in this lab |
| --- | --- | --- |
| `workers.dev` | Instant public subdomain hosted by Cloudflare | Yes |
| Routes | Attach a Worker to traffic for an existing Cloudflare zone | No |
| Custom Domains | Make a Worker the origin for a domain or subdomain | No |

## Observability and Operations

### Example Log Evidence

`wrangler tail --format json` captured the Worker executing at the edge with real request metadata:

```json
{
  "logs": [
    {
      "message": [
        "request",
        {
          "path": "/edge",
          "method": "GET",
          "colo": "IAD",
          "country": "US"
        }
      ]
    }
  ],
  "event": {
    "request": {
      "cf": {
        "colo": "IAD",
        "asn": 396982,
        "country": "US",
        "city": "North Charleston",
        "httpProtocol": "HTTP/1.1"
      }
    }
  },
  "scriptVersion": {
    "id": "4efba499-d942-4025-8c8d-b560184689d0"
  }
}
```

### Metrics Reviewed

Workers observability was enabled in `wrangler.jsonc`, and request activity plus deployment history were inspected through Wrangler and the Cloudflare dashboard. The main operational signal reviewed was request execution across successive deployments and rollback validation.

### Deployment History and Rollback

`wrangler deployments list` confirmed multiple versions and an explicit rollback:

| Created | Source | Message | Version |
| --- | --- | --- | --- |
| `2026-04-22T08:35:31.471Z` | deployment | `-` | `4efba499-d942-4025-8c8d-b560184689d0` |
| `2026-04-22T08:41:31.347Z` | deployment | `-` | `dd164221-2f42-446a-987b-e53b774717a6` |
| `2026-04-22T08:42:34.310Z` | deployment | `rollback validation` | `4efba499-d942-4025-8c8d-b560184689d0` |
| `2026-04-22T08:43:06.402Z` | deployment | `-` | `d0ac3c12-385e-48e4-a16b-6de2c4b228da` |

This demonstrates both forward deployment and rollback workflow without rebuilding infrastructure manually.

## Kubernetes vs Cloudflare Workers

| Aspect | Kubernetes | Cloudflare Workers |
| --- | --- | --- |
| Setup complexity | High: cluster, ingress, manifests, secrets, rollout strategy | Low: Worker project, bindings, deploy |
| Deployment speed | Slower, image build and cluster rollout required | Very fast, direct script deployment |
| Global distribution | Usually configured explicitly per region or cluster | Built in on Cloudflare edge |
| Cost for small apps | Often high because baseline cluster resources stay allocated | Usually lower for lightweight request-driven workloads |
| State and persistence | External systems such as DB, PV, Redis, object storage | KV, D1, R2, Durable Objects, external services |
| Control and flexibility | Very high, arbitrary containers and runtime control | More constrained, event-driven runtime model |
| Best use case | Long-running services, custom runtimes, complex platform needs | Edge APIs, lightweight webhooks, request transformation |

## When to Use Each

### Scenarios Favoring Kubernetes

- Stateful or long-running container workloads
- Workloads requiring custom OS packages or sidecars
- Complex release orchestration across many services
- Applications that depend on Docker images or background workers

### Scenarios Favoring Workers

- Lightweight HTTP APIs
- Edge personalization, redirects, or request filtering
- Low-ops public endpoints with global reach
- Small services that benefit from instant deployment and low idle cost

### Recommendation

Workers is the better fit for globally distributed, request-driven APIs with simple persistence needs. Kubernetes remains the stronger choice when container control, custom runtimes, or broader orchestration requirements dominate.

## Reflection

Compared with Kubernetes, the Worker setup felt significantly lighter because there was no cluster bootstrap, no image registry, and no rollout controller to operate. The main constraints were the non-container runtime model, platform-specific bindings, and regional networking quirks during verification. The biggest architectural change was treating the application as an edge script with platform services instead of a Docker-hosted web service.
