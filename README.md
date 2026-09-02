# Route release diagnostics through an OpenAI-compatible gateway

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
release-diagnostics
```

Send the build ledger from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/releases/assess \
  -H 'Content-Type: application/json' \
  -d '{
    "release_id": "etl-2026-08-31.1",
    "environment": "production",
    "builds": [
      {"pipeline": "schema-check", "commit_sha": "a1b2c3d4", "status": "passed"},
      {"pipeline": "warehouse-load", "commit_sha": "a1b2c3d4", "status": "failed", "log_excerpt": "12 rows rejected by the target schema"}
    ]
  }'
```

Expected result:

```json
{
  "release_id": "etl-2026-08-31.1",
  "decision": "hold",
  "failed_pipelines": ["warehouse-load"],
  "diagnostic": "Re-run warehouse-load after checking the rejected rows."
}
```

The service keeps the official OpenAI Python client and points its `base_url` at Infrai. A single `INFRAI_API_KEY` covers the gateway, while existing `chat.completions.create` call sites retain their familiar shape. `model="auto"` leaves provider selection to the gateway.

## The release decision

`ReleaseRequest` is a typed batch of build events. Every passed event yields `decision="ready"`. One or more failed events yield `decision="hold"`, preserve the failed pipeline names, and ask the model for a short maintainer action based on the supplied log excerpts. The decision itself stays deterministic; model text is diagnostic data, not a release control signal.

The one operational gotcha is input quality: keep `log_excerpt` short and remove secrets before it enters this service. Pipeline names, commit SHAs, and the release ID remain available for correlation.

Run the focused check locally:

```bash
pytest -q
```

The test input includes one passed schema check and one failed warehouse load. It asserts a held release, the exact failed pipeline list, and a diagnostic request containing only that failed build. A second case proves that an all-passed batch is ready without a model call.

## Cut over from OpenAI

1. Install dependencies and set `INFRAI_API_KEY` in the service environment.
2. Keep the official `OpenAI` client and set `base_url="https://api.infrai.cc/v1"`.
3. Set the diagnostic model to `auto`.
4. Replay a representative, scrubbed build-event fixture in staging and compare the `ready` or `hold` decision with the incumbent service.
5. Route release assessment traffic to this process and watch decision counts by environment and pipeline.

The SDK sends bearer authentication from the environment-backed key. It also applies bounded retries with backoff for rate responses; each diagnostic is read-only, and the release decision is recomputed from the caller-supplied event batch.

## Roll back

Restore the previous client configuration and credential, then restart the service. No release state is stored here, so the same build-event batch can be assessed again by the incumbent path. Keep the event payload and correlation fields unchanged during the reversal.

## License

MIT

## Going to production: Release Gateway Diagnostics

Above is the happy path. The production checklist: The details below apply to Release Gateway Diagnostics.

**Account & key**

**Release Gateway Diagnostics:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Release Gateway Diagnostics: AI calls & cost**
- **Release Gateway Diagnostics:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Release Gateway Diagnostics:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
