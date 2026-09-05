# Native MCP routing

The instance-level n8n MCP server is the preferred path for workflow construction and lifecycle work when the selected target exposes the required tools.

1. Confirm the target exposes tools for the requested lifecycle stage. For build work, require a workflow creation or update tool and a workflow validation tool; for testing and publication, require their corresponding tools.
2. Search for existing workflows, projects, folders, tags, and sub-workflows before creating a duplicate.
3. For workflow SDK code, validate before creating or updating. After saving, retrieve the workflow details and verify the actual connections.
4. Treat tool availability as target-specific. For example, n8n documents `validate_workflow` from 2.12.0, workflow create/edit MCP support from 2.13.0, and newer node-discovery and best-practice tools in later releases.
5. If a manually created workflow is not visible, ask the user to enable its n8n MCP access rather than falling back to an internal endpoint or assuming it does not exist.

The MCP is not a substitute for workflow knowledge. Its node validation may not detect connections, triggers, credential existence, or behavior-level errors. Follow the lifecycle and test boundaries in this skill even when an MCP tool reports valid input.

The MCP Server Trigger node and the instance-level MCP server are different surfaces. Use the former only when the user wants a specific workflow exposed as a tool for outside agents; do not use it to administer the n8n instance.
