export const MAX_FILE_BYTES = 96 * 1024;
const IDENTIFIER_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const COMMIT_PATTERN = /^[0-9a-f]{40}$/;
const SKILL_DIRECTORY_PATTERN = /^skills\/([a-z0-9]+(?:-[a-z0-9]+)*)\/([a-z0-9]+(?:-[a-z0-9]+)*)$/;

export interface SkillFile
{
  content_type: string;
  path: string;
  sha256: string;
  size_bytes: number;
}

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
      const indexResponse = await this.fetchImplementation(this.rawUrl(sourceCommit, "catalog/index.json"), {
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
    const response = await this.fetchImplementation(this.rawUrl(catalog.sourceCommit, `${skill.directory}/${file.path}`), {
      headers: { "User-Agent": "agentic-skills-mcp/0.1.0" },
      cf: { cacheEverything: true, cacheTtl: 3600 }
    } as RequestInit);
    if (!response.ok)
    {
      throw new CatalogError(`Skill file request failed with HTTP ${response.status}`);
    }
    const content = await response.text();
    if (new TextEncoder().encode(content).byteLength > MAX_FILE_BYTES)
    {
      throw new CatalogError("Downloaded skill file exceeds the maximum allowed size.");
    }
    if (await sha256(content) !== file.sha256)
    {
      throw new CatalogError("Downloaded skill file digest does not match the published manifest.");
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

  private rawUrl(sourceCommit: string, path: string): string
  {
    return `https://raw.githubusercontent.com/${this.repository}/${sourceCommit}/${path}`;
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
  const directoryMatch = typeof skill.directory === "string" ? SKILL_DIRECTORY_PATTERN.exec(skill.directory) : undefined;
  return typeof skill.id === "string" && IDENTIFIER_PATTERN.test(skill.id)
    && typeof skill.name === "string" && typeof skill.description === "string"
    && typeof skill.version === "string" && typeof skill.category === "string"
    && directoryMatch !== undefined && directoryMatch !== null
    && directoryMatch[1] === skill.category && directoryMatch[2] === skill.id
    && typeof skill.risk === "string" && Array.isArray(skill.facets)
    && Array.isArray(skill.compatibility) && Array.isArray(skill.files)
    && skill.files.every((file) => typeof file.path === "string" && !file.path.includes("..")
      && typeof file.sha256 === "string" && /^[0-9a-f]{64}$/.test(file.sha256)
      && typeof file.size_bytes === "number" && file.size_bytes >= 0
      && typeof file.content_type === "string");
}
