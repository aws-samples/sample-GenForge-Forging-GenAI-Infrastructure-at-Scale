/**
 * Backend Plugin Registration Tests
 *
 * Verifies that the backend index.ts file properly imports and registers
 * all expected Backstage backend plugins. Parses the source file as text
 * to validate plugin registration without starting the backend.
 */

import * as fs from 'fs';
import * as path from 'path';

const BACKEND_INDEX_PATH = path.resolve(
  __dirname,
  '../../packages/backend/src/index.ts',
);

/**
 * Expected backend plugins that must be registered.
 * Maps a descriptive label to the npm package name.
 */
const EXPECTED_PLUGINS: Array<{ label: string; package: string }> = [
  // App
  { label: 'App Backend', package: '@backstage/plugin-app-backend' },
  { label: 'Proxy Backend', package: '@backstage/plugin-proxy-backend' },

  // Scaffolder
  {
    label: 'Scaffolder Backend',
    package: '@backstage/plugin-scaffolder-backend',
  },
  {
    label: 'Scaffolder GitHub Module',
    package: '@backstage/plugin-scaffolder-backend-module-github',
  },

  // TechDocs
  { label: 'TechDocs Backend', package: '@backstage/plugin-techdocs-backend' },

  // Auth
  { label: 'Auth Backend', package: '@backstage/plugin-auth-backend' },
  {
    label: 'Auth Guest Provider',
    package: '@backstage/plugin-auth-backend-module-guest-provider',
  },

  // Catalog
  { label: 'Catalog Backend', package: '@backstage/plugin-catalog-backend' },
  {
    label: 'Catalog Scaffolder Entity Model',
    package:
      '@backstage/plugin-catalog-backend-module-scaffolder-entity-model',
  },

  // Permission
  {
    label: 'Permission Backend',
    package: '@backstage/plugin-permission-backend',
  },
  {
    label: 'Permission Allow All Policy',
    package: '@backstage/plugin-permission-backend-module-allow-all-policy',
  },

  // Search
  { label: 'Search Backend', package: '@backstage/plugin-search-backend' },
  {
    label: 'Search Catalog Module',
    package: '@backstage/plugin-search-backend-module-catalog',
  },
  {
    label: 'Search TechDocs Module',
    package: '@backstage/plugin-search-backend-module-techdocs',
  },

  // Notifications & Signals
  {
    label: 'Notifications Backend',
    package: '@backstage/plugin-notifications-backend',
  },
  {
    label: 'Signals Backend',
    package: '@backstage/plugin-signals-backend',
  },
];

describe('Backend Plugin Registration', () => {
  let backendContent: string;

  beforeAll(() => {
    backendContent = fs.readFileSync(BACKEND_INDEX_PATH, 'utf-8');
  });

  describe('backend index.ts structure', () => {
    test('file exists', () => {
      expect(fs.existsSync(BACKEND_INDEX_PATH)).toBe(true);
    });

    test('imports createBackend', () => {
      expect(backendContent).toMatch(
        /import\s*\{\s*createBackend\s*\}\s*from\s*['"]@backstage\/backend-defaults['"]/,
      );
    });

    test('creates backend instance', () => {
      expect(backendContent).toMatch(/const\s+backend\s*=\s*createBackend\(/);
    });

    test('calls backend.start()', () => {
      expect(backendContent).toMatch(/backend\.start\(\)/);
    });

    test('uses backend.add() for plugin registration', () => {
      expect(backendContent).toMatch(/backend\.add\(/);
    });
  });

  describe('plugin imports and registration', () => {
    for (const plugin of EXPECTED_PLUGINS) {
      test(`registers ${plugin.label} (${plugin.package})`, () => {
        // Check that the package is imported (directly or via dynamic import in backend.add)
        expect(backendContent).toContain(plugin.package);
      });

      test(`${plugin.label} is added via backend.add()`, () => {
        // The pattern is: backend.add(import('package-name'))
        // which may span multiple lines
        const escapedPackage = plugin.package.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const addPattern = new RegExp(
          `backend\\.add\\(\\s*import\\(['"]${escapedPackage}['"]\\)`,
        );
        expect(backendContent).toMatch(addPattern);
      });
    }
  });

  describe('plugin categories', () => {
    test('has app plugins registered', () => {
      expect(backendContent).toContain('@backstage/plugin-app-backend');
    });

    test('has scaffolder plugins registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-scaffolder-backend',
      );
      expect(backendContent).toContain(
        '@backstage/plugin-scaffolder-backend-module-github',
      );
    });

    test('has auth plugins registered', () => {
      expect(backendContent).toContain('@backstage/plugin-auth-backend');
      expect(backendContent).toContain(
        '@backstage/plugin-auth-backend-module-guest-provider',
      );
    });

    test('has catalog plugins registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-catalog-backend',
      );
    });

    test('has permission plugins registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-permission-backend',
      );
      expect(backendContent).toContain(
        '@backstage/plugin-permission-backend-module-allow-all-policy',
      );
    });

    test('has search plugins registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-search-backend',
      );
      expect(backendContent).toContain(
        '@backstage/plugin-search-backend-module-catalog',
      );
      expect(backendContent).toContain(
        '@backstage/plugin-search-backend-module-techdocs',
      );
    });

    test('has techdocs plugin registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-techdocs-backend',
      );
    });

    test('has notifications plugins registered', () => {
      expect(backendContent).toContain(
        '@backstage/plugin-notifications-backend',
      );
      expect(backendContent).toContain(
        '@backstage/plugin-signals-backend',
      );
    });
  });

  describe('total plugin count', () => {
    test('registers at least 16 plugins', () => {
      const addCalls = backendContent.match(/backend\.add\(/g);
      expect(addCalls).toBeDefined();
      expect(addCalls!.length).toBeGreaterThanOrEqual(16);
    });
  });

  describe('code organization', () => {
    test('has section comments for plugin categories', () => {
      // The backend index.ts should have organizational comments
      expect(backendContent).toMatch(/\/\/\s*(App|Scaffolder|Auth|Catalog|Permission|Search|TechDocs|Notifications)/i);
    });
  });
});
