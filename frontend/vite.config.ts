import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { existsSync, readFileSync } from 'node:fs';
import path from 'path';
import { defineConfig } from 'vite';

const pkg = JSON.parse(
  readFileSync(path.resolve(__dirname, 'package.json'), 'utf-8'),
) as { dependencies: Record<string, string>; devDependencies: Record<string, string> };

const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };

const PYPROJECT_URL =
  'https://raw.githubusercontent.com/areebahmeddd/jobdex/main/backend/pyproject.toml';

const strip = (v: string) => v.replace(/^[\^~>=<*]+/, '').trim();

function parsePyVersions(content: string): Record<string, string> {
  const versions: Record<string, string> = {};
  for (const m of content.matchAll(
    /"([a-zA-Z0-9_-]+)(?:\[[\w,]+\])?>=([0-9][^",\s]+)"/g,
  )) {
    versions[m[1].toLowerCase()] = m[2];
  }
  return versions;
}

export default defineConfig(async () => {
  let pyVersions: Record<string, string> = {};

  const pyprojectPath = path.resolve(__dirname, '../backend/pyproject.toml');
  if (existsSync(pyprojectPath)) {
    pyVersions = parsePyVersions(readFileSync(pyprojectPath, 'utf-8'));
  } else {
    try {
      const res = await fetch(PYPROJECT_URL);
      if (res.ok) pyVersions = parsePyVersions(await res.text());
    } catch {
      // versions will be absent from badges
    }
  }

  const TECH_VERSIONS = {
    react: strip(allDeps['react'] ?? ''),
    typescript: strip(allDeps['typescript'] ?? ''),
    vite: strip(allDeps['vite'] ?? ''),
    leaflet: strip(allDeps['leaflet'] ?? ''),
    tailwindcss: strip(allDeps['tailwindcss'] ?? ''),
    fastapi: pyVersions['fastapi'] ?? '',
    uvicorn: pyVersions['uvicorn'] ?? '',
    sqlalchemy: pyVersions['sqlalchemy'] ?? '',
    alembic: pyVersions['alembic'] ?? '',
    apscheduler: pyVersions['apscheduler'] ?? '',
    httpx2: pyVersions['httpx2'] ?? '',
    tenacity: pyVersions['tenacity'] ?? '',
    rapidfuzz: pyVersions['rapidfuzz'] ?? '',
  } as const;

  return {
    plugins: [react(), tailwindcss()],
    define: {
      __TECH_VERSIONS__: JSON.stringify(TECH_VERSIONS),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 3000,
    },
  };
});
