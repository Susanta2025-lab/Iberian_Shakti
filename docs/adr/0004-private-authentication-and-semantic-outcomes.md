# ADR 0004: Private authentication and semantic provider outcomes

- Status: Accepted
- Date: 2026-10-28

## Context

Phase 2 needs private header/query credentials and semantic HTTP-200 error
outcomes without weakening ADR 0002. This records the accepted
[assessment](../codex/reports/phase_2_readiness_assessment.md), §§M–N/R, before
implementation. Provider parsing and live authentication remain later work.

## Decision

Add a private fixed-HTTPS-origin GET request policy to the existing synchronous
HttpRetriever, not another HTTP client/retry engine. API requests require an
explicit origin policy. Header and query authentication are narrow private
value objects: `x-api-key` header for future ESIOS, `securityToken` query for
future ENTSO-E. Credentials never enter safe contracts/locators/provenance.
Private URL and header objects omit repr and have no serialization API. The
policy rejects origin changes, userinfo, fragments, duplicate credential query
parameters and invalid header/credential values before I/O. Identity encoding,
TLS verification, trust_env=False, zero redirects, raw streaming, phase/attempt/
operation budgets and existing retries stay unchanged. Legacy anonymous OMIE
uses the original path; private HTTP 401/403 become terminal auth/authorization
codes. No provider-specific classification/retry override is implemented now.

Load only the selected provider's existing ESIOS_API_TOKEN or ENTSOE_API_TOKEN
explicitly from an injected environment mapping or os.environ at invocation.
No dotenv/import-time read, real credential tests or unrelated credential
requirements. SecretStr storage is excluded from settings serialization/repr;
loader errors have static safe messages. As an initial application bound, tokens
are 8–4096 printable non-whitespace ASCII characters, not a claim about provider
formats. Anonymous sources return without reading a credential environment.

Before constructing a successful RawPayload, reject a body that echoes the
active credential (literal, URL-quoted or JSON-escaped UTF-8 forms). Never redact
and archive changed bytes as originals. Return a controlled permanent
`sensitive_response` failure, no payload/hash/archive/parse, with only safe
status/attempt diagnostics. Omit allowlisted HTTP observations if they contain
an active credential. Authenticated nonidentity bodies cannot be safely checked
without decoding; reject them before normal publication. This narrow guard does
not claim general DLP, detection of arbitrary transformed secrets, or protection
against malicious code deliberately putting secrets in application identifiers.
Non-200 bodies remain unarchived diagnostics and are never logged.

Keep the existing closed logging boundary, suppress transport debug and translate
exceptions to controlled codes without unchecked text. Sensitive response and
invalid private request errors never enter a retry loop. No registration, login,
refresh, paid access or provider network call is part of Stage 1.

Separate transport retrieval from semantic parsing. New version-2 parse events
represent success (positive count), source-unavailable/no-data (zero), provider
rejection (auth/authorization/quota/domain/request codes, zero), or content/profile/
time-semantics failure (zero). A complete safe HTTP-200 acknowledgement is
archived first as a successful retrieval, then receives an unsuccessful semantic
parse event. It is never relabelled HTTP 404. Legacy version-1 parse rules stay
price-only. Provider-specific acknowledgement grammar and classification belong
to future provider packages; Stage 1 tests use synthetic parsers only.

## Alternatives considered

Persisting a redacted transport URL mixes two responsibilities. Secrets in query
contracts or generic request dictionaries leak through serialization/validation.
Redacting response bytes violates original-byte integrity. A general DLP system,
authentication framework, provider registry and duplicate retry client are not
required. Keeping every HTTP-200 response as successful data loses provider
semantic failures.

## Consequences

Test header/query injection using MockTransport, static failures, origin pinning,
synthetic-token echoes, errors/logging, absent credentials and immutable sidecars.
Test valid HTTP-200 no-data/error archival before semantic outcomes. Retain all
Phase 1 regressions/offline network guard. No new dependency or provider parser
is authorized by this ADR. Existing archive objects are neither migrated nor
rewritten; new event types use their explicit versioned readers.
