import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'path';
import { defineConfig, type Plugin } from 'vite';
import { canonicalFor, ROUTE_META, SITE_URL } from './src/lib/routeMeta';

const pkg = JSON.parse(
  readFileSync(path.resolve(__dirname, 'package.json'), 'utf-8'),
) as { dependencies: Record<string, string>; devDependencies: Record<string, string> };

const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };

const PYPROJECT_URL =
  'https://raw.githubusercontent.com/areebahmeddd/jobdex/main/backend/pyproject.toml';

const strip = (v: string) => v.replace(/^[\^~>=<*]+/, '').trim();

const escapeHtml = (v: string) =>
  v.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

function routeShells(): Plugin {
  return {
    name: 'jobdex:route-shells',
    apply: 'build',
    closeBundle() {
      const outDir = path.resolve(__dirname, 'dist');
      const shell = path.join(outDir, 'index.html');
      if (!existsSync(shell)) return;

      const base = readFileSync(shell, 'utf-8');

      for (const [route, meta] of Object.entries(ROUTE_META)) {
        if (route === '/') continue;

        const title = escapeHtml(meta.title);
        const description = escapeHtml(meta.description);
        const canonical = canonicalFor(route);

        const html = base
          .replace(/<title>[\s\S]*?<\/title>/, `<title>${title}</title>`)
          .replace(
            /(<meta name="description"[\s\S]*?content=")[\s\S]*?(")/,
            `$1${description}$2`,
          )
          .replace(
            /(<link rel="canonical" href=")[^"]*(")/,
            `$1${canonical}$2`,
          )
          .replace(
            /(<meta property="og:title" content=")[^"]*(")/,
            `$1${title}$2`,
          )
          .replace(
            /(<meta property="og:description"[\s\S]*?content=")[\s\S]*?(")/,
            `$1${description}$2`,
          )
          .replace(/(<meta property="og:url" content=")[^"]*(")/, `$1${canonical}$2`)
          .replace(
            /(<meta name="twitter:title" content=")[^"]*(")/,
            `$1${title}$2`,
          )
          .replace(
            /(<meta name="twitter:description"[\s\S]*?content=")[\s\S]*?(")/,
            `$1${description}$2`,
          );

        const dir = path.join(outDir, route.replace(/^\//, ''));
        mkdirSync(dir, { recursive: true });
        writeFileSync(path.join(dir, 'index.html'), html);
      }

      const rules = Object.keys(ROUTE_META)
        .filter((route) => route !== '/')
        .map((route) => `${route.padEnd(20)} ${route}/index.html   200`)
        .join('\n');

      writeFileSync(
        path.join(outDir, '_redirects'),
        `# Generated at build time from src/lib/routeMeta.ts - do not edit by hand.\n` +
          `# Each known route resolves to its own prerendered head; unknown paths\n` +
          `# fall through to the SPA entry so client-side routing can 404 them.\n` +
          `${rules}\n${'/*'.padEnd(20)} /index.html         200\n`,
      );

      const probe = readFileSync(path.join(outDir, 'faq', 'index.html'), 'utf-8');
      if (!probe.includes(`${SITE_URL}/faq`)) {
        this.error('route-shells: canonical substitution did not apply');
      }
      if (!probe.includes(`content="FAQ | JobDex"`)) {
        this.error('route-shells: social tag substitution did not apply');
      }
    },
  };
}

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
      pyVersions = {};
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
    plugins: [react(), tailwindcss(), routeShells()],
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
