import { describe, expect, it } from "vitest";
import { CatalogError, GitHubCatalogSource, pageSkills, searchSkills } from "../src/catalog";
import worker from "../src/index";

const skill = {
  id: "example-skill", name: "example-skill", description: "Automates example workflow tasks.", version: "1.0.0",
  category: "infrastructure-and-operations", facets: ["automation"], risk: "moderate", compatibility: [],
  files: [{ path: "SKILL.md", sha256: "a".repeat(64), size_bytes: 12, content_type: "text/markdown" }]
};

describe("catalog discovery", () => {
  it("ranks a matching skill and pages results", () => {
    const catalog = { sourceCommit: "b".repeat(40), index: { schema_version: "1.0" as const, skills: [skill] } };
    expect(searchSkills(catalog, "automates", undefined, undefined)).toEqual([skill]);
    expect(pageSkills([skill], 0, 1)).toEqual({ items: [skill], nextCursor: undefined });
  });

  it("uses the last valid catalog during a transient source failure", async () => {
    let failed = false;
    const mockFetch = async (url: string) => {
      if (failed) return new Response("unavailable", { status: 503 });
      if (url.includes("git/ref")) return Response.json({ object: { sha: "b".repeat(40) } });
      return Response.json({ schema_version: "1.0", skills: [skill] });
    };
    const source = new GitHubCatalogSource(mockFetch as typeof fetch, "digows/agentic-skills", "main", 0);
    await source.load();
    failed = true;
    await expect(source.load()).resolves.toMatchObject({ sourceCommit: "b".repeat(40) });
  });

  it("rejects a malformed index", async () => {
    const mockFetch = async (url: string) => url.includes("git/ref")
      ? Response.json({ object: { sha: "b".repeat(40) } })
      : Response.json({ schema_version: "1.0", skills: [{ id: "../unsafe" }] });
    const source = new GitHubCatalogSource(mockFetch as typeof fetch, "digows/agentic-skills", "main", 0);
    await expect(source.load()).rejects.toBeInstanceOf(CatalogError);
  });

  it("rejects a downloaded file whose digest differs from the manifest", async () => {
    const mockFetch = async (url: string) => {
      if (url.includes("git/ref")) return Response.json({ object: { sha: "b".repeat(40) } });
      if (url.endsWith("catalog/index.json")) return Response.json({ schema_version: "1.0", skills: [skill] });
      return new Response("different-content");
    };
    const source = new GitHubCatalogSource(mockFetch as typeof fetch, "digows/agentic-skills", "main", 0);
    const catalog = await source.load();
    await expect(source.getFile(catalog, skill, "SKILL.md")).rejects.toBeInstanceOf(CatalogError);
  });

  it("serves MCP at the root endpoint only", async () => {
    const initializeResponse = await worker.fetch(new Request("https://skills.example/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "test", version: "1.0.0" } }
      })
    }), {}, {} as ExecutionContext);
    expect(initializeResponse.status).toBe(200);
    await expect(initializeResponse.text()).resolves.toContain("agentic-skills");

    const legacyPathResponse = await worker.fetch(new Request("https://skills.example/mcp"), {}, {} as ExecutionContext);
    expect(legacyPathResponse.status).toBe(404);
  });
});
