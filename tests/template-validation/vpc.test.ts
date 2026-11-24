/**
 * VPC Foundation Template Validation Tests
 *
 * Validates the VPC template YAML structure, parameter groups, steps,
 * and skeleton files for the GenForge VPC Foundation template.
 */

import path from 'path';
import {
  loadTemplate,
  validateSchema,
  validateParameterGroups,
  validateSteps,
  validateSkeletonFiles,
  getTemplateMetadata,
  getParameterGroupTitles,
  getGroupProperties,
  getPropertyDefinition,
} from '../helpers/template-validator';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/foundation/vpc',
);

describe('VPC Foundation Template Validation', () => {
  let template: any;

  beforeAll(async () => {
    template = await loadTemplate(path.join(TEMPLATE_DIR, 'template.yaml'));
  });

  describe('Schema', () => {
    test('has valid apiVersion', () => {
      expect(template.apiVersion).toBe('scaffolder.backstage.io/v1beta3');
    });

    test('has kind Template', () => {
      expect(template.kind).toBe('Template');
    });

    test('has correct metadata.name', () => {
      expect(template.metadata.name).toBe('genforge-vpc-template');
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has aws tag', () => {
      expect(template.metadata.tags).toContain('aws');
    });

    test('has vpc tag', () => {
      expect(template.metadata.tags).toContain('vpc');
    });

    test('has foundation tag', () => {
      expect(template.metadata.tags).toContain('foundation');
    });

    test('has correct spec.type', () => {
      expect(template.spec.type).toBe('foundation');
    });

    test('has correct spec.owner', () => {
      expect(template.spec.owner).toBe('platform-team');
    });

    test('has a title', () => {
      expect(template.metadata.title).toBeDefined();
      expect(template.metadata.title.length).toBeGreaterThan(0);
    });

    test('has a description', () => {
      expect(template.metadata.description).toBeDefined();
      expect(template.metadata.description.length).toBeGreaterThan(0);
    });

    test('passes full schema validation', () => {
      const result = validateSchema(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Parameters', () => {
    test('has exactly 4 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(4);
    });

    test('first group is Component Information', () => {
      expect(template.spec.parameters[0].title).toBe('Component Information');
    });

    test('second group is AWS Configuration', () => {
      expect(template.spec.parameters[1].title).toBe('AWS Configuration');
    });

    test('third group is VPC Configuration', () => {
      expect(template.spec.parameters[2].title).toBe('VPC Configuration');
    });

    test('last group is Repository Configuration', () => {
      expect(template.spec.parameters[3].title).toBe(
        'Repository Configuration',
      );
    });

    test('passes parameter group validation', () => {
      const result = validateParameterGroups(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('name field has correct pattern', () => {
      const nameProperty = getPropertyDefinition(
        template,
        'Component Information',
        'name',
      );
      expect(nameProperty).toBeDefined();
      expect(nameProperty.pattern).toBe('^[a-z0-9-]+$');
      expect(nameProperty.type).toBe('string');
    });

    test('name field has maxLength', () => {
      const nameProperty = getPropertyDefinition(
        template,
        'Component Information',
        'name',
      );
      expect(nameProperty.maxLength).toBe(50);
    });

    test('owner field uses OwnerPicker', () => {
      const ownerProperty = getPropertyDefinition(
        template,
        'Component Information',
        'owner',
      );
      expect(ownerProperty).toBeDefined();
      expect(ownerProperty['ui:field']).toBe('OwnerPicker');
    });

    test('awsRegion has valid enum values', () => {
      const regionProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'awsRegion',
      );
      expect(regionProperty).toBeDefined();
      expect(regionProperty.enum).toContain('us-east-1');
      expect(regionProperty.enum).toContain('us-west-2');
      expect(regionProperty.enum).toContain('eu-west-1');
    });

    test('awsAccountId uses EntityPicker', () => {
      const accountProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'awsAccountId',
      );
      expect(accountProperty).toBeDefined();
      expect(accountProperty['ui:field']).toBe('EntityPicker');
    });

    test('environment has dev/staging/prod', () => {
      const envProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'environment',
      );
      expect(envProperty).toBeDefined();
      expect(envProperty.enum).toEqual(['dev', 'staging', 'prod']);
    });

    test('has vpcCidr with pattern', () => {
      const cidrProperty = getPropertyDefinition(
        template,
        'VPC Configuration',
        'vpcCidr',
      );
      expect(cidrProperty).toBeDefined();
      expect(cidrProperty.type).toBe('string');
      expect(cidrProperty.pattern).toBeDefined();
      expect(cidrProperty.default).toBe('10.0.0.0/16');
    });

    test('has availabilityZones', () => {
      const azProperty = getPropertyDefinition(
        template,
        'VPC Configuration',
        'availabilityZones',
      );
      expect(azProperty).toBeDefined();
      expect(azProperty.type).toBe('integer');
      expect(azProperty.enum).toEqual([2, 3]);
    });

    test('has enableNatGateway boolean', () => {
      const natProperty = getPropertyDefinition(
        template,
        'VPC Configuration',
        'enableNatGateway',
      );
      expect(natProperty).toBeDefined();
      expect(natProperty.type).toBe('boolean');
      expect(natProperty.default).toBe(true);
    });

    test('has singleNatGateway boolean', () => {
      const singleNatProperty = getPropertyDefinition(
        template,
        'VPC Configuration',
        'singleNatGateway',
      );
      expect(singleNatProperty).toBeDefined();
      expect(singleNatProperty.type).toBe('boolean');
    });

    test('has enableVpcEndpoints boolean', () => {
      const endpointsProperty = getPropertyDefinition(
        template,
        'VPC Configuration',
        'enableVpcEndpoints',
      );
      expect(endpointsProperty).toBeDefined();
      expect(endpointsProperty.type).toBe('boolean');
      expect(endpointsProperty.default).toBe(true);
    });

    test('repoUrl uses RepoUrlPicker', () => {
      const repoProperty = getPropertyDefinition(
        template,
        'Repository Configuration',
        'repoUrl',
      );
      expect(repoProperty).toBeDefined();
      expect(repoProperty['ui:field']).toBe('RepoUrlPicker');
    });
  });

  describe('Steps', () => {
    test('has exactly 3 steps', () => {
      expect(template.spec.steps).toHaveLength(3);
    });

    test('first step is fetch:template', () => {
      expect(template.spec.steps[0].action).toBe('fetch:template');
    });

    test('second step is publish:github', () => {
      expect(template.spec.steps[1].action).toBe('publish:github');
    });

    test('third step is catalog:register', () => {
      expect(template.spec.steps[2].action).toBe('catalog:register');
    });

    test('fetch:template points to ./skeleton', () => {
      expect(template.spec.steps[0].input.url).toBe('./skeleton');
    });

    test('publish:github creates private repo', () => {
      expect(template.spec.steps[1].input.repoVisibility).toBe('private');
    });

    test('publish:github uses main as default branch', () => {
      expect(template.spec.steps[1].input.defaultBranch).toBe('main');
    });

    test('passes step validation', () => {
      const result = validateSteps(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Skeleton Files', () => {
    test('has all required skeleton files', () => {
      validateSkeletonFiles(TEMPLATE_DIR, [
        'skeleton/cdk/app.py',
        'skeleton/cdk/stack.py',
        'skeleton/cdk/requirements.txt',
        'skeleton/cdk/cdk.json',
        'skeleton/.github/workflows/deploy.yml',
        'skeleton/.github/workflows/destroy.yml',
        'skeleton/catalog-info.yaml',
        'skeleton/README.md',
      ]);
    });
  });

  describe('Output', () => {
    test('has output links', () => {
      expect(template.spec.output).toBeDefined();
      expect(template.spec.output.links).toBeDefined();
      expect(template.spec.output.links.length).toBeGreaterThan(0);
    });

    test('has repository output link', () => {
      const repoLink = template.spec.output.links.find(
        (l: any) => l.title === 'Repository',
      );
      expect(repoLink).toBeDefined();
    });

    test('has catalog output link', () => {
      const catalogLink = template.spec.output.links.find(
        (l: any) => l.title === 'Open in Catalog',
      );
      expect(catalogLink).toBeDefined();
    });
  });
});
