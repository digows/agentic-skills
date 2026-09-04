import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";
import { CatalogError, findSkill, GitHubCatalogSource, listSkills, pageSkills, searchSkills } from "./catalog";

const source = new GitHubCatalogSource(fetch);
const LIMIT_SCHEMA = z.number().int().min(1).max(25).default(10);
const CURSOR_SCHEMA = z.number().int().min(0).default(0);
const IDENTIFIER_SCHEMA = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).max(80);

function createServer(): McpServer
{
  const server = new McpServer({ name: "agentic-skills", version: "0.1.0" });

  server.registerTool("list_skills", {
    description: "List compact metadata for published portable Agent Skills. Use filters and pagination before requesting full skill content.",
    inputSchema: {
      category: z.string().max(80).optional(),
      cursor: CURSOR_SCHEMA,
      limit: LIMIT_SCHEMA,
      risk: z.enum(["low", "moderate", "high", "critical"]).optional()
    }
  }, async ({ category, cursor, limit, risk }) => respond(async () => {
    const catalog = await source.load();
    const page = pageSkills(listSkills(catalog, category, risk), cursor, limit);
    return { source_commit: catalog.sourceCommit, skills: page.items, next_cursor: page.nextCursor };
  }));

  server.registerTool("search_skills", {
    description: "Search published portable Agent Skills by name, description, and catalogue facets. Returns compact metadata only.",
    inputSchema: {
      category: z.string().max(80).optional(),
      limit: LIMIT_SCHEMA,
      query: z.string().min(1).max(200),
      risk: z.enum(["low", "moderate", "high", "critical"]).optional()
    }
  }, async ({ category, limit, query, risk }) => respond(async () => {
    const catalog = await source.load();
    return { source_commit: catalog.sourceCommit, skills: searchSkills(catalog, query, category, risk).slice(0, limit) };
  }));

  server.registerTool("get_skill", {
    description: "Retrieve the canonical SKILL.md for one published skill, together with its immutable source commit and SHA-256 digest.",
    inputSchema: { id: IDENTIFIER_SCHEMA }
  }, async ({ id }) => respond(async () => {
    const catalog = await source.load();
    const skill = findSkill(catalog, id);
    const content = await source.getFile(catalog, skill, "SKILL.md");
    return { source_commit: catalog.sourceCommit, skill, content };
  }));

  server.registerTool("get_skill_file", {
    description: "Retrieve one manifest-declared text file from a published skill. The server rejects undeclared paths and verifies SHA-256.",
    inputSchema: {
      id: IDENTIFIER_SCHEMA,
      path: z.string().min(1).max(240).refine((path) => !path.startsWith("/") && !path.split("/").includes(".."))
    }
  }, async ({ id, path }) => respond(async () => {
    const catalog = await source.load();
    const skill = findSkill(catalog, id);
    const content = await source.getFile(catalog, skill, path);
    return { source_commit: catalog.sourceCommit, id: skill.id, path, content };
  }));

  return server;
}

async function respond(operation: () => Promise<unknown>)
{
  try
  {
    const payload = await operation();
    return { content: [{ type: "text" as const, text: JSON.stringify(payload) }] };
  }
  catch (error)
  {
    const message = error instanceof CatalogError ? error.message : "Catalog service is temporarily unavailable.";
    return { content: [{ type: "text" as const, text: JSON.stringify({ error: message }) }], isError: true };
  }
}

export default {
  fetch(request, environment, executionContext)
  {
    if (new URL(request.url).pathname === "/healthz")
    {
      return Response.json({ service: "agentic-skills-mcp", status: "ok" });
    }
    return createMcpHandler(createServer)(request, environment, executionContext);
  }
} satisfies ExportedHandler;
