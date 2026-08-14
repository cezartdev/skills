#!/usr/bin/env node

/**
 * sync-versions.mjs
 * 
 * Synchronizes the root package.json version across all skill documentation
 * files (docs/<skill>/README.md) and any future plugin manifests.
 * 
 * Usage:
 *   node scripts/sync-versions.mjs         # Syncs all files in-place
 *   node scripts/sync-versions.mjs --check # Exits with 1 if any file is out of sync
 */

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';

const isCheck = process.argv.includes('--check');
const rootDir = process.cwd();

// Read root package.json version
const pkgPath = resolve(rootDir, 'package.json');
if (!existsSync(pkgPath)) {
  console.error(`[sync-versions] package.json not found at ${pkgPath}`);
  process.exit(1);
}

const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
const currentVersion = pkg.version;

if (!currentVersion) {
  console.error('[sync-versions] No version found in package.json');
  process.exit(1);
}

console.log(`[sync-versions] Current package.json version: ${currentVersion}`);

let hasMismatch = false;

// 1. Scan docs/*/README.md
const docsDir = resolve(rootDir, 'docs');
if (existsSync(docsDir)) {
  const entries = readdirSync(docsDir);
  for (const entry of entries) {
    const skillDocPath = join(docsDir, entry, 'README.md');
    if (existsSync(skillDocPath) && statSync(skillDocPath).isFile()) {
      const content = readFileSync(skillDocPath, 'utf8');
      const versionRegex = /(>\s*\*\*Version\*\*:\s*`)([^`]+)(`)/g;

      if (versionRegex.test(content)) {
        const matches = [...content.matchAll(versionRegex)];
        for (const match of matches) {
          const docVersion = match[2];
          if (docVersion !== currentVersion) {
            if (isCheck) {
              console.error(`[FAIL] ${skillDocPath}: Version mismatch (found: ${docVersion}, expected: ${currentVersion})`);
              hasMismatch = true;
            } else {
              const updatedContent = content.replace(versionRegex, `$1${currentVersion}$3`);
              writeFileSync(skillDocPath, updatedContent, 'utf8');
              console.log(`[UPDATED] ${skillDocPath}: ${docVersion} -> ${currentVersion}`);
            }
          } else {
            console.log(`[OK] ${skillDocPath} is up-to-date (${currentVersion})`);
          }
        }
      }
    }
  }
}

if (isCheck) {
  if (hasMismatch) {
    console.error('\n[sync-versions] Check failed: Some documentation or manifest versions are out of sync.');
    process.exit(1);
  } else {
    console.log('\n[sync-versions] Check passed: All versions match package.json.');
    process.exit(0);
  }
}
