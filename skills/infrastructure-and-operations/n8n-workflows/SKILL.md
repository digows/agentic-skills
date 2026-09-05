---
name: n8n-workflows
description: Design, inspect, edit, validate, test, publish, and hand off n8n workflows. Prefer the instance-level n8n MCP workflow tools when available; otherwise use the selected instance's documented Public API v1 and OpenAPI contract. Use when creating or changing n8n workflows, nodes, expressions, connections, triggers, workflow tests, activation, publishing, folders, or workflow MCP access.
license: Apache-2.0
---

# n8n Workflows

Manage the workflow lifecycle: plan, build, validate, test, publish, and hand off. This skill is transport-aware but not transport-coupled: it prefers the official instance-level MCP workflow tools and falls back to the selected target's Public API v1 only when that operation is documented there.

## Route the task

1. Identify the explicit n8n target profile and whether the request is inspect, create, edit, test, publish, activate, deactivate, archive, or hand off.
2. Inspect the available n8n MCP tools. Use the MCP path when it provides the required workflow, node-definition, validation, and test operations. Read [`references/mcp-routing.md`](references/mcp-routing.md) first.
3. If the native MCP is unavailable or lacks the required operation, use the selected target's Public API only after following [`references/api-fallback.md`](references/api-fallback.md).
4. Do not use UI/internal REST endpoints, scrape the editor, or infer support from another n8n target.

## Lifecycle

1. **Plan.** Clarify the trigger, inputs, outputs, side effects, target project/folder, schedule/time zone, retry/error behavior, and whether an equivalent workflow or sub-workflow already exists.
2. **Build or edit.** Prefer native nodes. Name workflows and nodes by their action and purpose. Add a concise workflow description explaining both what it does and why. Preserve existing workflow behavior unless the requested change requires otherwise.
3. **Validate.** Validate workflow structure and node configuration through the selected MCP tools where available. Then retrieve the saved workflow and verify connections, trigger configuration, and the intended active state. Validation alone is insufficient.
4. **Test.** Use representative data and isolate or pin downstream side effects when the target supports it. Ask before a test can write data, call an external service, invoke a sub-workflow, execute code, or otherwise cause user-visible effects.
5. **Publish.** Publish, activate, or deactivate only after validation and a suitable test are clean, and only with explicit authority for that external effect.
6. **Hand off.** State how the workflow triggers, where it sends or returns data, how to verify it, relevant failure modes, and any user-side setup still required.

Read [`references/validation-and-testing.md`](references/validation-and-testing.md) before testing, publishing, activating, or deactivating a workflow.

## Authentication

Resolve access to the n8n target using the target-bound local profile. A valid stored credential must be reused without prompting; request setup or reauthorization only when the selected profile is missing, unavailable, or rejected. Never try another target's credential after a `401` or `403`.

Credentials used *inside* a workflow are separate from credentials used to access the n8n target. Store workflow integration secrets in n8n's credential system, not in workflow JSON, expressions, SDK code, variables, chat, or a node text field. When multiple suitable n8n credentials exist, ask the user which one to bind. See [`references/credentials.md`](references/credentials.md).

## Upstream compatibility

The n8n MCP workflow surface is version-gated and may be unavailable even when Public API v1 exists. Treat the selected target's exposed MCP tools, their documented versions, and its OpenAPI document as the authority for that target. Never claim an MCP-only workflow feature is available through the Public API fallback.

Before a version-sensitive, restricted, or optional operation, inspect the available tool or OpenAPI schema for the selected target. Stop and report an unsupported operation instead of guessing an alternative payload or endpoint.

## Safety boundaries

- Treat publishing, activation, deactivation, deletion, archival, credential binding, source-control changes, and changing a live trigger as external effects.
- Before editing an existing workflow, retrieve its current definition and preserve unrelated nodes, connections, settings, and metadata.
- Workflows created manually in the n8n UI may be invisible to the instance-level MCP until the user enables workflow MCP access. Ask the user to confirm that setting before concluding the workflow does not exist.
- Do not claim the Public API provides generic manual workflow execution unless the selected target's OpenAPI explicitly exposes it.
- If the user asks for a draft-only change but the available operation would publish or alter an active workflow externally, stop and explain the boundary.
