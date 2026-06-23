#!/usr/bin/env node
// No-mock tripwire: fails if any production module imports lib/mock or
// references MockFallback. lib/mock.ts itself, and test files, are exempt.
// This is the mechanical guarantee behind "nothing in prod falls back to
// fake data" (see SYSTEM_STATUS_AND_REMEDIATION.md, Phase 0).

import { globSync, readFileSync } from 'node:fs'
import { resolve, relative } from 'node:path'

const SRC_DIR = resolve(import.meta.dirname, '..', 'src')

const EXEMPT_FILES = new Set(['lib/mock.ts'])
const FORBIDDEN_PATTERNS = [
  { pattern: /from\s+['"][^'"]*lib\/mock['"]/, label: "imports from 'lib/mock'" },
  { pattern: /\bMockFallback\b/, label: 'references MockFallback' },
]

const files = globSync('**/*.{ts,tsx}', { cwd: SRC_DIR }).map((f) => resolve(SRC_DIR, f))
const violations = []

for (const file of files) {
  const rel = relative(SRC_DIR, file).replace(/\\/g, '/')
  if (EXEMPT_FILES.has(rel)) continue

  const content = readFileSync(file, 'utf-8')
  for (const { pattern, label } of FORBIDDEN_PATTERNS) {
    if (pattern.test(content)) {
      violations.push(`${rel}: ${label}`)
    }
  }
}

if (violations.length > 0) {
  console.error('No-mock tripwire failed — production code must not use mock fallback:\n')
  for (const v of violations) console.error(`  - ${v}`)
  console.error(`\n${violations.length} violation(s). lib/mock.ts may only be used by tests.`)
  process.exit(1)
}

console.log(`No-mock tripwire passed (${files.length} files checked).`)
