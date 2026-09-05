# Authentication contract

This contract applies to every published skill whose catalogue entry declares an authentication policy. Local skills must declare it when they require credentials; federated upstream entries declare either this policy or `null`. The catalogue MCP server distributes this contract and canonical skill files; it does not resolve, store, validate, or transmit credentials.

## Portable rules

An authenticated skill must contain an `## Authentication` section and declare an `authentication` object in `catalog.json`.

The skill must:

1. Resolve the explicit target before resolving any credential. A target can be a canonical base URL, account, tenant, project, or another stable resource identity defined by the upstream service.
2. Bind a credential to the exact target or named local profile. Never select a credential by hostname suffix, guess a compatible target, or use a generic credential as fallback for a configured target.
3. Attempt non-interactive resolution first. A valid existing credential must permit subsequent use without another prompt.
4. Request setup or reauthorization only when no target profile exists, the credential is unavailable, or the upstream service rejects or revokes it. Use the clipboard onboarding flow below for API keys; do not ask the user to paste a secret into chat.
5. Stop on authentication or authorization failure. A `401` or `403` must not trigger a retry with another target's credential. A `404` must not be treated as evidence that the resource belongs to another target.
6. Keep secrets out of prompts, logs, command traces, URLs, source control, evaluation fixtures, and skill files. Examples may show only variable or reference placeholders.

The skill may perform one documented, low-impact validation request after resolving a profile when the upstream API supports it. It must record no secret value or authorization header.

## Credential onboarding UX

All API-key skills use one provider-agnostic onboarding flow when the selected target has no usable local profile:

1. Ask the user: `Copy the API key to your system clipboard, then reply ready.`
2. Read the clipboard only after that explicit reply and only when the harness exposes clipboard-reading capability.
3. Persist the value in the target-bound local profile and immediately use that profile for the requested operation. Never echo the value.
4. Reuse the valid profile silently on later requests.
5. If the harness cannot read the clipboard, say that in one sentence and ask the user to register the same target-bound profile through its normal local credential mechanism. Do not provide provider-specific setup instructions in the canonical skill.

The portable contract standardizes the interaction and the target-to-credential mapping. It does not require a credential runtime, dictate a secret store, or assume that every agent can read the clipboard.

## Authentication metadata

`catalog.json.authentication` records the portable policy, not a secret, host inventory, or secret-manager implementation:

```json
{
  "methods": ["api-key"],
  "target_binding": "exact-target",
  "prompting": "when-missing-or-invalid",
  "failure_behavior": "stop",
  "onboarding": "clipboard-when-available"
}
```

`methods` is informative and may list the upstream authentication methods supported by the skill, such as `api-key`, `oauth2`, `bearer-token`, or `client-certificate`. The other four fields are fixed contract invariants.

## Local profiles and adapters

Host-specific configuration is private runtime state, not catalogue content. A harness adapter may use an OS keychain, environment variables, a secret manager, or an encrypted local file. Whatever the mechanism, it must implement the same logical mapping:

```text
explicit target or profile -> credential reference -> credential value at execution time
```

For example, a local profile can associate `https://n8n.example.com` with the reference `N8N_API_KEY_PRODUCTION`. The value behind that reference is resolved by the local harness; it is never placed in the repository. A public skill must not name an organization's hosts, private secret locations, or live credential references.
