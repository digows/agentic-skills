# Credential boundaries

There are two independent credential domains:

1. **Agent-to-n8n access.** The local harness resolves a credential bound to the selected n8n target profile. It is never stored in this skill or in the workflow definition.
2. **Workflow-to-service access.** n8n nodes refer to credentials stored by n8n. Select the existing correct credential by its ID or ask the user to choose when more than one matches.

Never place an integration secret in workflow JSON, an expression, a Set/Edit Fields node, a variable, node SDK code, or chat. Prefer a native node and its native credential type. If no native node fits, use the appropriate n8n HTTP Request credential type.

Do not create an integration credential from a secret pasted into conversation. Tell the user the exact credential type to create in n8n, then bind the created credential. If a secret was pasted, treat it as exposed and tell the user to rotate it.
