import { describe, expect, it } from "vitest";
import { CatalogError, GitHubCatalogSource, pageSkills, searchSkills } from "../src/catalog";
import worker from "../src/index";

const skill = {
  id: "example-skill", name: "example-skill", description: "Automates example workflow tasks.", version: "1.0.0",
  directory: "skills/infrastructure-and-operations/example-skill", category: "infrastructure-and-operations", facets: ["automation"], risk: "moderate", compatibility: [],
  origin: { kind: "local" as const },
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

  it("rejects a skill whose directory does not match its category and identifier", async () => {
    const mockFetch = async (url: string) => url.includes("git/ref")
      ? Response.json({ object: { sha: "b".repeat(40) } })
      : Response.json({ schema_version: "1.0", skills: [{ ...skill, directory: "skills/software-engineering/other-skill" }] });
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

  it("retrieves an immutable upstream skill and applies its section overlay", async () => {
    const upstreamContent = "---\nname: upstream\ndescription: Example.\n---\n# Example\n\n## Safety\n\nOriginal rule.\n\n## End\n";
    const upstreamSkill = {
      ...skill,
      id: "upstream-skill",
      name: "upstream-skill",
      directory: "upstreams/upstream-skill",
      origin: {
        kind: "upstream" as const,
        repository: "example/official-skills",
        commit: "c".repeat(40),
        license: "Apache-2.0",
        reviewed_at: "2026-09-05",
        overlay: [{ operation: "replace" as const, section: "## Safety", content: "Replacement rule." }]
      },
      files: [{
        path: "SKILL.md",
        source_path: "skills/example/SKILL.md",
        sha256: await digest(upstreamContent),
        size_bytes: new TextEncoder().encode(upstreamContent).byteLength,
        content_type: "text/markdown"
      }]
    };
    const mockFetch = async (url: string) => {
      if (url.includes("git/ref")) return Response.json({ object: { sha: "b".repeat(40) } });
      if (url.endsWith("catalog/index.json")) return Response.json({ schema_version: "1.0", skills: [upstreamSkill] });
      if (url.includes("example/official-skills/")) return new Response(upstreamContent);
      return new Response("not found", { status: 404 });
    };
    const source = new GitHubCatalogSource(mockFetch as typeof fetch, "digows/agentic-skills", "main", 0);
    const catalog = await source.load();
    await expect(source.getFile(catalog, upstreamSkill, "SKILL.md")).resolves.toContain("Replacement rule.");
    await expect(source.getFile(catalog, upstreamSkill, "SKILL.md")).resolves.not.toContain("Original rule.");
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

async function digest(content: string): Promise<string>
{
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
