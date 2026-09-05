# Validation, testing, and publication

Validation checks structure; it is not proof that a workflow is safe or correct.

Before publishing or changing an active workflow:

1. Validate the workflow and relevant node configuration through the selected target's available tools.
2. Retrieve the saved workflow and compare connections, trigger, settings, credential bindings, and active state against the intended change.
3. Test with representative, safe input. Identify which downstream nodes can still cause external writes or calls; request explicit confirmation before those effects can run.
4. Confirm the user has completed any required credential, project, folder, or target-service setup.
5. Only then request or use authority to publish, activate, deactivate, archive, or otherwise change live behavior.

After publication, hand off the trigger mechanism, expected output or destination, first verification step, operational failure signals, and unresolved user actions.
