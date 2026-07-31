import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { findForbiddenGuidance, findSkillInventoryIssues } from '../scripts/audit-gpt-routing';

describe('GPT routing guidance audit', () => {
  it.each([
    '**Medium**: implementation and debugging.',
    'Coding is Medium.',
    'Every Codex child runs at Medium.',
    'Use Low for search.',
    'Use xhigh for implementation lanes.',
    'Use Opus 4.8 for the review.',
  ])('rejects forbidden guidance: %s', (contents) => {
    expect(findForbiddenGuidance(contents)).toHaveLength(1);
  });

  it.each([
    '**Medium**: search, documentation, inventories, and test execution.',
    'Documentation lookup is Medium.',
    'Use Medium for bounded read-only evidence gathering.',
    'Implementation uses High.',
    'Do not use `low`, `minimal`, or `none` for GPT work.',
    'Do not use xhigh for coding without explicit user authorization.',
    'Opus 4.8 is prohibited for execution and review.',
    'Do not select Opus 4.8 as a fallback.',
  ])('allows valid guidance: %s', (contents) => {
    expect(findForbiddenGuidance(contents)).toEqual([]);
  });

  it('reports the matching line', () => {
    const contents = ['Implementation uses High.', '', 'Coding is Medium.'].join('\n');

    expect(findForbiddenGuidance(contents)).toEqual([expect.objectContaining({ lineNumber: 3 })]);
  });
});

describe('repository skill inventory audit', () => {
  const canonicalRoot = path.resolve('/repo/.agents/skills');
  const canonicalEntries = [
    { name: 'git-check', isDirectory: true },
    { name: 'sybil', isDirectory: true },
  ];

  it('accepts the exact canonical inventory and matching mirrors', () => {
    const mirrors = canonicalEntries.map((entry) => ({
      name: entry.name,
      isSymbolicLink: true,
      resolvedPath: path.join(canonicalRoot, entry.name),
    }));

    expect(findSkillInventoryIssues(canonicalEntries, mirrors, canonicalRoot)).toEqual([]);
  });

  it('reports missing and unexpected entries', () => {
    const canonical = [
      { name: 'git-check', isDirectory: true },
      { name: 'main-integration', isDirectory: true },
    ];
    const mirrors = canonical.map((entry) => ({
      name: entry.name,
      isSymbolicLink: true,
      resolvedPath: path.join(canonicalRoot, entry.name),
    }));

    expect(findSkillInventoryIssues(canonical, mirrors, canonicalRoot)).toEqual([
      { filePath: path.join('.agents/skills', 'sybil'), label: 'missing canonical skill' },
      { filePath: path.join('.claude/skills', 'sybil'), label: 'missing skill mirror' },
      {
        filePath: path.join('.agents/skills', 'main-integration'),
        label: 'unexpected canonical skill entry',
      },
      {
        filePath: path.join('.claude/skills', 'main-integration'),
        label: 'unexpected skill mirror entry',
      },
    ]);
  });

  it('reports invalid mirror states', () => {
    expect(
      findSkillInventoryIssues(
        canonicalEntries,
        [
          { name: 'git-check', isSymbolicLink: false, resolvedPath: null },
          { name: 'sybil', isSymbolicLink: true, resolvedPath: null },
        ],
        canonicalRoot
      )
    ).toEqual([
      {
        filePath: path.join('.claude/skills', 'git-check'),
        label: 'skill mirror is not a symlink',
      },
      { filePath: path.join('.claude/skills', 'sybil'), label: 'skill mirror is dangling' },
    ]);

    expect(
      findSkillInventoryIssues(
        canonicalEntries,
        [
          {
            name: 'git-check',
            isSymbolicLink: true,
            resolvedPath: path.join(canonicalRoot, 'sybil'),
          },
          {
            name: 'sybil',
            isSymbolicLink: true,
            resolvedPath: path.join(canonicalRoot, 'sybil'),
          },
        ],
        canonicalRoot
      )
    ).toContainEqual({
      filePath: path.join('.claude/skills', 'git-check'),
      label: 'skill mirror resolves to the wrong canonical skill',
    });
  });
});
