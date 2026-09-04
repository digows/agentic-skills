---
name: rita
description: Analyze Zeek metadata with RITA safely.
license: Apache-2.0
compatibility: RITA v5 with ClickHouse-backed datasets.
metadata: portable network threat analytics procedure.
allowed-tools: command-execution,file-read
---
# RITA network threat analytics

Use RITA to investigate Zeek metadata for command-and-control-like behavior. This skill is read-only by default: it analyzes existing logs and datasets, reports evidence, and does not block traffic, change firewall rules, or collect continuous PCAP.

## When to use

- A user asks to import Zeek logs, inspect RITA results, or investigate beaconing, DNS/C2, long-lived sessions, prevalence, or threat-intelligence hits.
- A scheduled pipeline needs an incremental Zeek-to-RITA analysis step.
- A security finding needs corroboration before escalation.

Do not use it to declare a host compromised from one score, to block traffic, or to configure a network sensor without explicit authorization.

## Prerequisites

- RITA v5 configured with a reachable ClickHouse service and a dedicated database user.
- Zeek logs from the intended sensor, with timestamps and the selected internal subnets documented.
- A command-execution tool for `rita` and a file-reading tool for logs and configuration.
- Authorization before importing sensitive telemetry or changing persistent RITA state.

## Procedure

1. Confirm the evidence boundary: identify sensor interface, log directory, time window, internal subnets, and whether the view omits switched lateral traffic. Completion: the scope and blind spots are explicit.
2. Verify ClickHouse connectivity and the RITA configuration before an import. Completion: the database endpoint responds and the configured RITA user can authenticate.
3. Check that Zeek produces fresh rotated `conn.log` and relevant DNS, HTTP, and SSL/TLS logs. Completion: timestamps advance and logs are readable without modifying them.
4. Import only the intended dataset. For hourly ingestion, use a bounded rolling import after log rotation; for older historical data, use a deliberate non-rolling import strategy. Completion: RITA reports a completed import and the dataset has current timestamps.
5. Query non-interactively with `rita view --stdout <dataset>`. Put view flags before the dataset name. Completion: CSV output is captured without requiring a TTY.
6. Correlate signals before escalation: threat-intelligence match, repeatable beaconing, low-prevalence destination, DNS behavior, session duration, destination ownership, and asset role. Completion: each finding has evidence and a confidence boundary.
7. Preserve a compact, sanitized finding record: time window, source/destination, rule or score, corroborating evidence, uncertainty, and recommended next observation. Completion: no credentials, full packet payloads, or unrelated telemetry are included.

## Interpretation

- A high or critical RITA score is a lead, not proof of compromise. Newly built datasets and legitimate periodic services can look like beaconing.
- Treat a confirmed threat-intelligence match as high-priority evidence, but verify timestamps, destination, source role, and feed freshness before claiming impact.
- Empty custom threat-intelligence-feed directories can produce warnings; distinguish that from an unavailable configured online feed.
- DNS records with blank queries and TLS records without server names may be skipped by RITA. Report coverage loss rather than silently treating skipped records as clean traffic.

## Safety boundaries

- Never use RITA output alone to quarantine, block, reboot, or reconfigure a client.
- Require explicit approval for imports that rebuild a dataset, retention changes, credential changes, external notifications, or network-device actions.
- Keep credentials in the harness secret store, never in skill files, command history, logs, or reports.
- Prefer a short retention window and metadata-only analysis unless the user explicitly authorizes broader collection.

## Verification

- The database is reachable and the intended dataset is selected.
- Import completion and dataset timestamps prove ingestion; a Running pod or process does not.
- `rita view --stdout` returns parseable CSV in a non-interactive environment.
- Findings state source, destination, time window, evidence, confidence, and blind spots.
- No enforcement or external notification occurred without separate authorization.
