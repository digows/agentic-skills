export const MAX_FILE_BYTES = 96 * 1024;
const IDENTIFIER_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const COMMIT_PATTERN = /^[0-9a-f]{40}$/;
const REPOSITORY_PATTERN = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const SKILL_DIRECTORY_PATTERN = /^skills\/([a-z0-9]+(?:-[a-z0-9]+)*)\/([a-z0-9]+(?:-[a-z0-9]+)*)$/;
const UPSTREAM_DIRECTORY_PATTERN = /^upstreams\/([a-z0-9]+(?:-[a-z0-9]+)*)$/;

export interface SkillFile
{
  content_type: string;
  path: string;
  sha256: string;
  size_bytes: number;
  source_path?: string;
}

export interface OverlayOperation
{
  operation: "append" | "replace" | "remove";
  section: string;
  content?: string;
}

export type SkillOrigin =
  | { kind: "local"; }
  | {
    kind: "upstream";
    repository: string;
    commit: string;
    license: string;
    reviewed_at: string;
    overlay: OverlayOperation[];
  };

export interface SkillSummary
{
  category: string;
  compatibility: Array<Record<string, unknown>>;
  description: string;
  directory: string;
  facets: string[];
  files: SkillFile[];
  id: string;
  name: string;
  origin: SkillOrigin;
  risk: string;
  version: string;
}

interface SkillIndex
{
  schema_version: "1.0";
  skills: SkillSummary[];
}

export interface LoadedCatalog
{
  index: SkillIndex;
  sourceCommit: string;
}

export class CatalogError extends Error
{
  public constructor(message: string)
  {
    super(message);
    this.name = "CatalogError";
  }
}

export class GitHubCatalogSource
{
  private cachedCatalog: LoadedCatalog | undefined;
  private cacheExpiresAt = 0;

  public constructor(
    private readonly fetchImplementation: typeof fetch,
    private readonly repository = "digows/agentic-skills",
    private readonly branch = "main",
    private readonly cacheTtlMilliseconds = 300_000
  )
  {
  }

  public async load(): Promise<LoadedCatalog>
  {
    if (this.cachedCatalog !== undefined && Date.now() < this.cacheExpiresAt)
    {
      return this.cachedCatalog;
    }

    try
    {
      const sourceCommit = await this.fetchCommit();
      const indexResponse = await this.fetchImplementation(this.rawUrl(this.repository, sourceCommit, "catalog/index.json"), {
        headers: { "User-Agent": "agentic-skills-mcp/0.1.0" },
        cf: { cacheEverything: true, cacheTtl: 300 }
      } as RequestInit);
      if (!indexResponse.ok)
      {
        throw new CatalogError(`GitHub index request failed with HTTP ${indexResponse.status}`);
      }
      const index = validateIndex(await indexResponse.json());
      const loadedCatalog = { index, sourceCommit };
      this.cachedCatalog = loadedCatalog;
      this.cacheExpiresAt = Date.now() + this.cacheTtlMilliseconds;
      return loadedCatalog;
    }
    catch (error)
    {
      if (this.cachedCatalog !== undefined)
      {
        return this.cachedCatalog;
      }
      throw error;
    }
  }

  public async getFile(catalog: LoadedCatalog, skill: SkillSummary, path: string): Promise<string>
  {
    const file = skill.files.find((candidate) => candidate.path === path);
    if (file === undefined)
    {
      throw new CatalogError("Requested file is not declared by the published skill manifest.");
    }
    if (file.size_bytes > MAX_FILE_BYTES)
    {
      throw new CatalogError("Requested file exceeds the maximum allowed size.");
    }
    const source = skill.origin.kind === "local"
      ? { repository: this.repository, commit: catalog.sourceCommit, path: `${skill.directory}/${file.path}`, overlay: [] as OverlayOperation[] }
      : { repository: skill.origin.repository, commit: skill.origin.commit, path: file.source_path ?? "", overlay: file.path === "SKILL.md" ? skill.origin.overlay : [] };
    if (!source.path)
    {
      throw new CatalogError("Upstream skill file is missing its declared source path.");
    }
    const response = await this.fetchImplementation(this.rawUrl(source.repository, source.commit, source.path), {
      headers: { "User-Agent": "agentic-skills-mcp/0.1.0" },
      cf: { cacheEverything: true, cacheTtl: 3600 }
    } as RequestInit);
    if (!response.ok)
    {
      throw new CatalogError(`Skill file request failed with HTTP ${response.status}`);
    }
    const upstreamContent = await response.text();
    if (new TextEncoder().encode(upstreamContent).byteLength > MAX_FILE_BYTES)
    {
      throw new CatalogError("Downloaded skill file exceeds the maximum allowed size.");
    }
    if (await sha256(upstreamContent) !== file.sha256)
    {
      throw new CatalogError("Downloaded skill file digest does not match the published manifest.");
    }
    const content = applyOverlay(upstreamContent, source.overlay);
    if (new TextEncoder().encode(content).byteLength > MAX_FILE_BYTES)
    {
      throw new CatalogError("Resolved skill file exceeds the maximum allowed size.");
    }
    return content;
  }

  private async fetchCommit(): Promise<string>
  {
    const response = await this.fetchImplementation(`https://api.github.com/repos/${this.repository}/git/ref/heads/${this.branch}`, {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "agentic-skills-mcp/0.1.0"
      },
      cf: { cacheEverything: true, cacheTtl: 300 }
    } as RequestInit);
    if (!response.ok)
    {
      throw new CatalogError(`GitHub reference request failed with HTTP ${response.status}`);
    }
    const payload = await response.json() as { object?: { sha?: unknown } };
    const sourceCommit = payload.object?.sha;
    if (typeof sourceCommit !== "string" || !COMMIT_PATTERN.test(sourceCommit))
    {
      throw new CatalogError("GitHub reference did not return a commit SHA.");
    }
    return sourceCommit;
  }

  private rawUrl(repository: string, sourceCommit: string, path: string): string
  {
    return `https://raw.githubusercontent.com/${repository}/${sourceCommit}/${path}`;
  }
}

export function findSkill(catalog: LoadedCatalog, identifier: string): SkillSummary
{
  if (!IDENTIFIER_PATTERN.test(identifier))
  {
    throw new CatalogError("Skill identifier must be lowercase kebab-case.");
  }
  const skill = catalog.index.skills.find((candidate) => candidate.id === identifier);
  if (skill === undefined)
  {
    throw new CatalogError("Published skill was not found.");
  }
  return skill;
}

export function listSkills(catalog: LoadedCatalog, category: string | undefined, risk: string | undefined): SkillSummary[]
{
  return catalog.index.skills.filter((skill) =>
    (category === undefined || skill.category === category) &&
    (risk === undefined || skill.risk === risk)
  );
}

export function searchSkills(catalog: LoadedCatalog, query: string, category: string | undefined, risk: string | undefined): SkillSummary[]
{
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery)
  {
    throw new CatalogError("Search query must not be empty.");
  }
  return listSkills(catalog, category, risk)
    .map((skill) => ({ skill, score: scoreSkill(skill, normalizedQuery) }))
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score || left.skill.id.localeCompare(right.skill.id))
    .map((candidate) => candidate.skill);
}

export function pageSkills(skills: SkillSummary[], cursor: number, limit: number): { items: SkillSummary[]; nextCursor: number | undefined }
{
  const normalizedCursor = Math.max(0, cursor);
  const items = skills.slice(normalizedCursor, normalizedCursor + limit);
  const nextCursor = normalizedCursor + items.length < skills.length ? normalizedCursor + items.length : undefined;
  return { items, nextCursor };
}

async function sha256(content: string): Promise<string>
{
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function scoreSkill(skill: SkillSummary, query: string): number
{
  const name = skill.name.toLocaleLowerCase();
  const description = skill.description.toLocaleLowerCase();
  const facets = skill.facets.join(" ").toLocaleLowerCase();
  return (name === query ? 8 : name.includes(query) ? 4 : 0)
    + (description.includes(query) ? 2 : 0)
    + (facets.includes(query) ? 1 : 0);
}

function validateIndex(value: unknown): SkillIndex
{
  if (typeof value !== "object" || value === null)
  {
    throw new CatalogError("Catalog index must be an object.");
  }
  const index = value as Partial<SkillIndex>;
  if (index.schema_version !== "1.0" || !Array.isArray(index.skills))
  {
    throw new CatalogError("Catalog index has an unsupported schema.");
  }
  const skillIds = new Set<string>();
  for (const skill of index.skills)
  {
    if (!isValidSkill(skill) || skillIds.has(skill.id))
    {
      throw new CatalogError("Catalog index contains an invalid or duplicate skill.");
    }
    skillIds.add(skill.id);
  }
  return index as SkillIndex;
}

function isValidSkill(value: unknown): value is SkillSummary
{
  if (typeof value !== "object" || value === null)
  {
    return false;
  }
  const skill = value as Partial<SkillSummary>;
  const localDirectoryMatch = typeof skill.directory === "string" ? SKILL_DIRECTORY_PATTERN.exec(skill.directory) : undefined;
  const upstreamDirectoryMatch = typeof skill.directory === "string" ? UPSTREAM_DIRECTORY_PATTERN.exec(skill.directory) : undefined;
  return typeof skill.id === "string" && IDENTIFIER_PATTERN.test(skill.id)
    && typeof skill.name === "string" && typeof skill.description === "string"
    && typeof skill.version === "string" && typeof skill.category === "string"
    && typeof skill.risk === "string" && Array.isArray(skill.facets)
    && Array.isArray(skill.compatibility) && Array.isArray(skill.files)
    && skill.files.every((file) => typeof file.path === "string" && !file.path.includes("..")
      && typeof file.sha256 === "string" && /^[0-9a-f]{64}$/.test(file.sha256)
      && typeof file.size_bytes === "number" && file.size_bytes >= 0
      && typeof file.content_type === "string")
    && isValidOrigin(skill.origin, skill.id, skill.category, localDirectoryMatch, upstreamDirectoryMatch, skill.files);
}

function isValidOrigin(
  origin: unknown,
  identifier: string,
  category: string,
  localDirectoryMatch: RegExpExecArray | null | undefined,
  upstreamDirectoryMatch: RegExpExecArray | null | undefined,
  files: SkillFile[]
): origin is SkillOrigin
{
  if (typeof origin !== "object" || origin === null)
  {
    return false;
  }
  const candidate = origin as {
    kind?: unknown;
    repository?: unknown;
    commit?: unknown;
    license?: unknown;
    reviewed_at?: unknown;
    overlay?: unknown;
  };
  if (candidate.kind === "local")
  {
    return localDirectoryMatch !== undefined && localDirectoryMatch !== null
      && localDirectoryMatch[1] === category
      && localDirectoryMatch[2] === identifier
      && Object.keys(candidate).length === 1
      && files.every((file) => file.source_path === undefined);
  }
  if (candidate.kind !== "upstream")
  {
    return false;
  }
  return upstreamDirectoryMatch !== undefined && upstreamDirectoryMatch !== null
    && upstreamDirectoryMatch[1] === identifier
    && typeof candidate.repository === "string" && REPOSITORY_PATTERN.test(candidate.repository)
    && typeof candidate.commit === "string" && COMMIT_PATTERN.test(candidate.commit)
    && typeof candidate.license === "string" && candidate.license.length > 0
    && typeof candidate.reviewed_at === "string" && /^\d{4}-\d{2}-\d{2}$/.test(candidate.reviewed_at)
    && Array.isArray(candidate.overlay) && candidate.overlay.every(isValidOverlayOperation)
    && files.every((file) => typeof file.source_path === "string" && !file.source_path.startsWith("/") && !file.source_path.split("/").includes(".."));
}

function isValidOverlayOperation(value: unknown): value is OverlayOperation
{
  if (typeof value !== "object" || value === null)
  {
    return false;
  }
  const operation = value as Partial<OverlayOperation>;
  if (typeof operation.section !== "string" || !/^#{1,6}\s+\S.*$/.test(operation.section))
  {
    return false;
  }
  if (operation.operation === "remove")
  {
    return Object.keys(operation).length === 2;
  }
  return (operation.operation === "append" || operation.operation === "replace")
    && typeof operation.content === "string" && operation.content.trim().length > 0
    && Object.keys(operation).length === 3;
}

export function applyOverlay(content: string, operations: OverlayOperation[]): string
{
  return operations.reduce((resolvedContent, operation) => applyOverlayOperation(resolvedContent, operation), content);
}

function applyOverlayOperation(content: string, operation: OverlayOperation): string
{
  const headingPattern = /^#{1,6}\s+.*$/gm;
  const headings = Array.from(content.matchAll(headingPattern));
  const targetHeadings = headings.filter((heading) => heading[0].trimEnd() === operation.section);
  if (targetHeadings.length !== 1)
  {
    throw new CatalogError(`Overlay section '${operation.section}' was not found exactly once in the upstream skill.`);
  }
  const target = targetHeadings[0];
  const targetStart = target.index ?? 0;
  const targetEnd = targetStart + target[0].length;
  const targetLevel = target[0].match(/^#+/)?.[0].length ?? 0;
  const nextHeading = headings.find((heading) => (heading.index ?? 0) > targetStart && (heading[0].match(/^#+/)?.[0].length ?? 0) <= targetLevel);
  const sectionEnd = nextHeading?.index ?? content.length;
  if (operation.operation === "remove")
  {
    return `${content.slice(0, targetStart)}${content.slice(sectionEnd)}`.replace(/\n{3,}/g, "\n\n");
  }
  const normalizedContent = operation.content?.trim() ?? "";
  if (operation.operation === "replace")
  {
    return `${content.slice(0, targetEnd)}\n\n${normalizedContent}\n\n${content.slice(sectionEnd).replace(/^\n+/, "")}`;
  }
  return `${content.slice(0, sectionEnd).replace(/\s*$/, "")}\n\n${normalizedContent}\n\n${content.slice(sectionEnd).replace(/^\n+/, "")}`;
}
