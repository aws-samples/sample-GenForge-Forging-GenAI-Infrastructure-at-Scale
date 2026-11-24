/**
 * Catalog Entity Validation Tests
 *
 * Tests that the Backstage catalog entity YAML files (system, org, AWS accounts)
 * are well-formed and contain the expected entities for GenForge.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'yaml';

const CATALOG_DIR = path.resolve(__dirname, '../../catalog');

/**
 * Parse a YAML file that may contain multiple documents separated by ---.
 */
function parseMultiDocYaml(filePath: string): any[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  return yaml.parseAllDocuments(content).map(doc => doc.toJSON());
}

describe('Catalog Entity Validation', () => {
  describe('genforge-system.yaml', () => {
    let system: any;

    beforeAll(() => {
      const filePath = path.join(CATALOG_DIR, 'genforge-system.yaml');
      const content = fs.readFileSync(filePath, 'utf-8');
      system = yaml.parse(content);
    });

    test('file exists', () => {
      expect(
        fs.existsSync(path.join(CATALOG_DIR, 'genforge-system.yaml')),
      ).toBe(true);
    });

    test('has correct apiVersion', () => {
      expect(system.apiVersion).toBe('backstage.io/v1alpha1');
    });

    test('has kind System', () => {
      expect(system.kind).toBe('System');
    });

    test('has name genforge', () => {
      expect(system.metadata.name).toBe('genforge');
    });

    test('has a title', () => {
      expect(system.metadata.title).toBeDefined();
      expect(system.metadata.title).toBe('GenForge');
    });

    test('has a description', () => {
      expect(system.metadata.description).toBeDefined();
      expect(system.metadata.description.length).toBeGreaterThan(0);
    });

    test('has relevant tags', () => {
      expect(system.metadata.tags).toBeDefined();
      expect(system.metadata.tags).toContain('genai');
      expect(system.metadata.tags).toContain('aws');
    });

    test('has owner platform-team', () => {
      expect(system.spec.owner).toBe('platform-team');
    });
  });

  describe('org.yaml', () => {
    let entities: any[];

    beforeAll(() => {
      entities = parseMultiDocYaml(path.join(CATALOG_DIR, 'org.yaml'));
    });

    test('file exists', () => {
      expect(fs.existsSync(path.join(CATALOG_DIR, 'org.yaml'))).toBe(true);
    });

    test('contains exactly 5 entities (4 groups + 1 user)', () => {
      expect(entities).toHaveLength(5);
    });

    test('contains 4 Group entities', () => {
      const groups = entities.filter(e => e.kind === 'Group');
      expect(groups).toHaveLength(4);
    });

    test('contains 1 User entity', () => {
      const users = entities.filter(e => e.kind === 'User');
      expect(users).toHaveLength(1);
    });

    test('has platform-team group', () => {
      const platformTeam = entities.find(
        e => e.kind === 'Group' && e.metadata.name === 'platform-team',
      );
      expect(platformTeam).toBeDefined();
      expect(platformTeam.spec.type).toBe('team');
    });

    test('has data-science-team group', () => {
      const dsTeam = entities.find(
        e => e.kind === 'Group' && e.metadata.name === 'data-science-team',
      );
      expect(dsTeam).toBeDefined();
      expect(dsTeam.spec.type).toBe('team');
    });

    test('has data-engineering-team group', () => {
      const deTeam = entities.find(
        e => e.kind === 'Group' && e.metadata.name === 'data-engineering-team',
      );
      expect(deTeam).toBeDefined();
      expect(deTeam.spec.type).toBe('team');
    });

    test('has devops-team group', () => {
      const devopsTeam = entities.find(
        e => e.kind === 'Group' && e.metadata.name === 'devops-team',
      );
      expect(devopsTeam).toBeDefined();
      expect(devopsTeam.spec.type).toBe('team');
    });

    test('has guest user', () => {
      const guest = entities.find(
        e => e.kind === 'User' && e.metadata.name === 'guest',
      );
      expect(guest).toBeDefined();
    });

    test('guest user is member of a team', () => {
      const guest = entities.find(
        e => e.kind === 'User' && e.metadata.name === 'guest',
      );
      expect(guest.spec.memberOf).toBeDefined();
      expect(guest.spec.memberOf.length).toBeGreaterThan(0);
    });

    test('all entities have correct apiVersion', () => {
      for (const entity of entities) {
        expect(entity.apiVersion).toBe('backstage.io/v1alpha1');
      }
    });
  });

  describe('aws-accounts.yaml', () => {
    let entities: any[];

    beforeAll(() => {
      entities = parseMultiDocYaml(
        path.join(CATALOG_DIR, 'aws-accounts.yaml'),
      );
    });

    test('file exists', () => {
      expect(
        fs.existsSync(path.join(CATALOG_DIR, 'aws-accounts.yaml')),
      ).toBe(true);
    });

    test('contains exactly 3 AWS account entities', () => {
      expect(entities).toHaveLength(3);
    });

    test('all entities are Resources', () => {
      for (const entity of entities) {
        expect(entity.kind).toBe('Resource');
      }
    });

    test('all entities have type aws-account', () => {
      for (const entity of entities) {
        expect(entity.spec.type).toBe('aws-account');
      }
    });

    test('has development account (111111111111)', () => {
      const devAccount = entities.find(
        e => e.metadata.name === '111111111111',
      );
      expect(devAccount).toBeDefined();
      expect(devAccount.metadata.title).toContain('Development');
    });

    test('has staging account (222222222222)', () => {
      const stagingAccount = entities.find(
        e => e.metadata.name === '222222222222',
      );
      expect(stagingAccount).toBeDefined();
      expect(stagingAccount.metadata.title).toContain('Staging');
    });

    test('has production account (333333333333)', () => {
      const prodAccount = entities.find(
        e => e.metadata.name === '333333333333',
      );
      expect(prodAccount).toBeDefined();
      expect(prodAccount.metadata.title).toContain('Production');
    });

    test('all accounts are owned by platform-team', () => {
      for (const entity of entities) {
        expect(entity.spec.owner).toBe('platform-team');
      }
    });

    test('all accounts belong to genforge system', () => {
      for (const entity of entities) {
        expect(entity.spec.system).toBe('genforge');
      }
    });

    test('all entities have correct apiVersion', () => {
      for (const entity of entities) {
        expect(entity.apiVersion).toBe('backstage.io/v1alpha1');
      }
    });

    test('all accounts have aws tag', () => {
      for (const entity of entities) {
        expect(entity.metadata.tags).toContain('aws');
      }
    });
  });
});
