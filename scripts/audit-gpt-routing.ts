import { lstatSync, readFileSync, readdirSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

type Requirement = {
  filePath: string;
  checks: Array<{ label: string; pattern: RegExp }>;
};

type Finding = {
  filePath: string;
  lineNumber: number;
  label: string;
};

export type CanonicalSkillEntry = {
  name: string;
  isDirectory: boolean;
};

export type MirrorSkillEntry = {
  name: string;
  isSymbolicLink: boolean;
  resolvedPath: string | null;
};

export type SkillInventoryIssue = {
  filePath: string;
  label: string;
};

const ROOT = process.cwd();

export const EXPECTED_SKILL_NAMES = ['git-check', 'sybil'] as const;

export function findSkillInventoryIssues(
  canonicalEntries: readonly CanonicalSkillEntry[],
  mirrorEntries: readonly MirrorSkillEntry[],
  canonicalRoot: string
): SkillInventoryIssue[] {
  const issues: SkillInventoryIssue[] = [];
  const expectedNames = new Set<string>(EXPECTED_SKILL_NAMES);
  const canonicalNames = new Set(canonicalEntries.map((entry) => entry.name));
  const mirrorNames = new Set(mirrorEntries.map((entry) => entry.name));

  for (const name of EXPECTED_SKILL_NAMES) {
    if (!canonicalNames.has(name)) {
      issues.push({
        filePath: path.join('.agents/skills', name),
        label: 'missing canonical skill',
      });
    }

    if (!mirrorNames.has(name)) {
      issues.push({
        filePath: path.join('.claude/skills', name),
        label: 'missing skill mirror',
      });
    }
  }

  for (const entry of canonicalEntries) {
    const filePath = path.join('.agents/skills', entry.name);

    if (!expectedNames.has(entry.name)) {
      issues.push({ filePath, label: 'unexpected canonical skill entry' });
    }

    if (!entry.isDirectory) {
      issues.push({ filePath, label: 'canonical skill entry is not a directory' });
    }
  }

  for (const entry of mirrorEntries) {
    const filePath = path.join('.claude/skills', entry.name);

    if (!expectedNames.has(entry.name)) {
      issues.push({ filePath, label: 'unexpected skill mirror entry' });
    }

    if (!entry.isSymbolicLink) {
      issues.push({ filePath, label: 'skill mirror is not a symlink' });
      continue;
    }

    if (entry.resolvedPath === null) {
      issues.push({ filePath, label: 'skill mirror is dangling' });
      continue;
    }

    if (path.resolve(entry.resolvedPath) !== path.resolve(canonicalRoot, entry.name)) {
      issues.push({ filePath, label: 'skill mirror resolves to the wrong canonical skill' });
    }
  }

  return issues;
}

const requirements: Requirement[] = [
  {
    filePath: '.codex/config.toml',
    checks: [
      { label: 'missing GPT-5.6 SOL model pin', pattern: /^model = "gpt-5\.6-sol"$/m },
      { label: 'missing High default effort', pattern: /^model_reasoning_effort = "high"$/m },
    ],
  },
  {
    filePath: 'AGENTS.md',
    checks: [
      { label: 'missing Fable owner route', pattern: /\*\*Fable High\*\* owns final/i },
      { label: 'missing GPT-5.6 SOL-only route', pattern: /GPT route uses GPT-5\.6 SOL only/i },
      {
        label: 'missing High implementation and judgment rule',
        pattern: /\*\*High\*\*:[\s\S]{0,220}coding[\s\S]{0,220}judgment-bearing\s+review/i,
      },
      {
        label: 'missing Medium evidence rule',
        pattern: /\*\*Medium\*\*:[\s\S]{0,220}search[\s\S]{0,220}read-only evidence gathering/i,
      },
      {
        label: 'missing user-gated XHigh boundary',
        pattern: /\*\*Extra High \(`xhigh`\)\*\*:[^\n]*explicitly requested/i,
      },
      {
        label: 'missing user-gated Ultra boundary',
        pattern: /\*\*Ultra\*\*:[^\n]*explicitly requested/i,
      },
      { label: 'missing Opus 4.8 prohibition', pattern: /Opus 4\.8 is prohibited/i },
    ],
  },
  {
    filePath: '.claude/CLAUDE.md',
    checks: [
      { label: 'missing root AGENTS handoff', pattern: /Read root `AGENTS\.md` first/i },
      { label: 'missing no-mirror rule', pattern: /do not mirror\s+those rules here/i },
    ],
  },
];

const prohibition = String.raw`\b(?:do not|must not|never|prohibited|forbidden)\b`;
const highWork = String.raw`(?:coding|implementation|debugging|bug fixes?|refactors?|integration|conflict resolution|architecture judgment|product judgment|judgment-bearing review)`;

const forbiddenGuidancePatterns = [
  {
    label: 'XHigh used without explicit user authorization',
    pattern: new RegExp(
      String.raw`^(?![^\r\n]*${prohibition})[^\r\n]*(?:use|select|run|default(?: to)?|remains?)\s+(?:Extra High|xhigh)\s+for\s+[^\r\n]{0,80}(?:coding|implementation|debugging|bug fixes?|refactors?|integration|review|fixes?|changes?|lanes?)`,
      'im'
    ),
  },
  { label: 'obsolete effort prompt', pattern: /Ultrathink/i },
  {
    label: 'GPT-5.6 SOL effort below High for implementation or judgment',
    pattern: new RegExp(
      String.raw`^(?![^\r\n]*${prohibition})[^\r\n]*(?:${highWork}[^\r\n]{0,80}\b(?:Medium|Low|Minimal|None)\b|\b(?:Medium|Low|Minimal|None)\b[^\r\n]{0,80}${highWork})`,
      'im'
    ),
  },
  {
    label: 'GPT-5.6 SOL effort below Medium',
    pattern: new RegExp(
      String.raw`^(?![^\r\n]*${prohibition})[^\r\n]*(?:\b(?:use|select|assign|route|run|default(?: to)?|uses?|runs?)\s+(?:at\s+)?(?:Low|Minimal|None)\b|model_reasoning_effort\s*=\s*["'](?:low|minimal|none)["'])`,
      'im'
    ),
  },
  {
    label: 'blanket Medium effort assignment',
    pattern: new RegExp(
      String.raw`^(?![^\r\n]*${prohibition})[^\r\n]*(?:(?:all GPT|all work|every (?:Codex )?child)[^\r\n]{0,80}\bMedium\b|\bMedium\b[^\r\n]{0,80}(?:all GPT|all work|every (?:Codex )?child))`,
      'im'
    ),
  },
  {
    label: 'Opus 4.8 selected despite repository prohibition',
    pattern: new RegExp(
      String.raw`^(?![^\r\n]*${prohibition})[^\r\n]*\b(?:use|select|assign|route|delegate\s+to|fall\s+back\s+to|fallback\s+to|execute\s+with|review\s+with)\s+Opus\s*4\.8\b`,
      'im'
    ),
  },
];

const removedPaths = [
  'docs/plans/2026-03-02-universal-threat-intel-hub-design.md',
  'docs/plans/2026-03-02-universal-threat-intel-hub.md',
  'docs/plans/2026-03-04-settings-page-redesign.md',
  '.reports/dead-code-analysis.md',
];

function isMissingPathError(error: unknown): boolean {
  if (!(error instanceof Error) || !('code' in error)) return false;
  return error.code === 'ENOENT' || error.code === 'ENOTDIR';
}

function pathEntryExists(filePath: string): boolean {
  try {
    lstatSync(filePath);
    return true;
  } catch (error) {
    if (isMissingPathError(error)) return false;
    throw error;
  }
}

function getLineNumber(contents: string, index: number): number {
  return contents.slice(0, index).split(/\r?\n/).length;
}

export function findForbiddenGuidance(
  contents: string
): Array<{ lineNumber: number; label: string }> {
  const findings: Array<{ lineNumber: number; label: string }> = [];

  for (const forbidden of forbiddenGuidancePatterns) {
    const match = forbidden.pattern.exec(contents);
    if (match) {
      findings.push({
        lineNumber: getLineNumber(contents, match.index),
        label: forbidden.label,
      });
    }
  }

  return findings;
}

function getFilesRecursively(directory: string): string[] {
  const files: string[] = [];

  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const absolutePath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      files.push(...getFilesRecursively(absolutePath));
    } else if (entry.isFile() && (entry.name.endsWith('.md') || entry.name.endsWith('.yaml'))) {
      files.push(path.relative(ROOT, absolutePath));
    }
  }

  return files;
}

export function runRoutingAudit(): number {
  const canonicalRoot = path.resolve(ROOT, '.agents/skills');
  const mirrorRoot = path.resolve(ROOT, '.claude/skills');
  const canonicalDirectoryEntries = readdirSync(canonicalRoot, { withFileTypes: true });
  const mirrorDirectoryEntries = readdirSync(mirrorRoot, { withFileTypes: true });
  const canonicalEntries = canonicalDirectoryEntries.map((entry) => ({
    name: entry.name,
    isDirectory: entry.isDirectory(),
  }));
  const mirrorEntries = mirrorDirectoryEntries.map((entry) => {
    let resolvedPath: string | null = null;

    if (entry.isSymbolicLink()) {
      try {
        resolvedPath = realpathSync(path.join(mirrorRoot, entry.name));
      } catch (error) {
        if (!isMissingPathError(error)) throw error;
      }
    }

    return {
      name: entry.name,
      isSymbolicLink: entry.isSymbolicLink(),
      resolvedPath,
    };
  });
  const findings: Finding[] = findSkillInventoryIssues(
    canonicalEntries,
    mirrorEntries,
    canonicalRoot
  ).map((issue) => ({ ...issue, lineNumber: 1 }));
  const skillNames = new Map<string, string>();

  for (const directory of canonicalDirectoryEntries.filter((entry) => entry.isDirectory())) {
    const skillPath = path.join('.agents/skills', directory.name, 'SKILL.md');
    const absoluteSkillPath = path.resolve(ROOT, skillPath);

    if (!pathEntryExists(absoluteSkillPath)) {
      findings.push({
        filePath: skillPath,
        lineNumber: 1,
        label: 'skill directory has no SKILL.md',
      });
      continue;
    }

    const contents = readFileSync(absoluteSkillPath, 'utf8');
    const name = contents.match(/^name:\s*["']?([^"'\r\n]+)["']?\s*$/m)?.[1]?.trim();

    if (!name) {
      findings.push({ filePath: skillPath, lineNumber: 1, label: 'skill frontmatter has no name' });
      continue;
    }

    if (name !== directory.name) {
      findings.push({
        filePath: skillPath,
        lineNumber: 1,
        label: 'skill name does not match directory',
      });
    }

    const priorPath = skillNames.get(name);
    if (priorPath) {
      findings.push({
        filePath: skillPath,
        lineNumber: 1,
        label: `duplicate skill name also used by ${priorPath}`,
      });
    } else {
      skillNames.set(name, skillPath);
    }

    const metadataPath = path.join('.agents/skills', directory.name, 'agents/openai.yaml');
    const absoluteMetadataPath = path.resolve(ROOT, metadataPath);

    if (!pathEntryExists(absoluteMetadataPath)) {
      findings.push({
        filePath: metadataPath,
        lineNumber: 1,
        label: 'skill has no agents/openai.yaml',
      });
    } else if (!readFileSync(absoluteMetadataPath, 'utf8').includes(`$${name}`)) {
      findings.push({
        filePath: metadataPath,
        lineNumber: 1,
        label: 'default prompt does not invoke its skill name',
      });
    }
  }

  for (const requirement of requirements) {
    const absolutePath = path.resolve(ROOT, requirement.filePath);

    if (!pathEntryExists(absolutePath)) {
      findings.push({
        filePath: requirement.filePath,
        lineNumber: 1,
        label: 'missing required file',
      });
      continue;
    }

    const contents = readFileSync(absolutePath, 'utf8');
    for (const check of requirement.checks) {
      if (!check.pattern.test(contents)) {
        findings.push({ filePath: requirement.filePath, lineNumber: 1, label: check.label });
      }
    }
  }

  const activeGuidanceFiles = [
    'AGENTS.md',
    'FRONTEND.md',
    '.claude/CLAUDE.md',
    '.claude/rules/claude-hooks.md',
    ...getFilesRecursively(canonicalRoot),
  ];

  for (const filePath of activeGuidanceFiles) {
    const absolutePath = path.resolve(ROOT, filePath);
    if (!pathEntryExists(absolutePath)) continue;

    const contents = readFileSync(absolutePath, 'utf8');

    for (const forbidden of findForbiddenGuidance(contents)) {
      findings.push({ filePath, ...forbidden });
    }
  }

  for (const filePath of removedPaths) {
    if (pathEntryExists(path.resolve(ROOT, filePath))) {
      findings.push({ filePath, lineNumber: 1, label: 'stale compatibility file still present' });
    }
  }

  if (findings.length === 0) {
    console.log('GPT-5.6 routing audit passed.');
    return 0;
  }

  console.error(`GPT-5.6 routing audit found ${findings.length} issue(s):`);
  for (const finding of findings) {
    console.error(`- ${finding.filePath}:${finding.lineNumber} ${finding.label}`);
  }

  return 1;
}

function isMainModule(): boolean {
  const entry = process.argv[1];
  return Boolean(entry && import.meta.url === pathToFileURL(path.resolve(entry)).href);
}

if (isMainModule()) {
  process.exitCode = runRoutingAudit();
}
