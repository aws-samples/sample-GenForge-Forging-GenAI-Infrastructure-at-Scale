/**
 * MLflow AI Gateway Template Validation Tests
 *
 * Validates the MLflow AI Gateway template YAML structure, parameter groups,
 * steps, and skeleton files.
 */

import path from 'path';
import {
  loadTemplate,
  validateSchema,
  validateParameterGroups,
  validateSteps,
  validateSkeletonFiles,
  getPropertyDefinition,
} from '../helpers/template-validator';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/mlflow/ai-gateway',
);

describe('MLflow AI Gateway Template Validation', () => {
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
      expect(template.metadata.name).toBe(
        'genforge-mlflow-ai-gateway-template',
      );
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has mlflow tag', () => {
      expect(template.metadata.tags).toContain('mlflow');
    });

    test('has fargate tag', () => {
      expect(template.metadata.tags).toContain('fargate');
    });

    test('has gateway tag', () => {
      expect(template.metadata.tags).toContain('gateway');
    });

    test('has correct spec.type', () => {
      expect(template.spec.type).toBe('mlflow');
    });

    test('has correct spec.owner', () => {
      expect(template.spec.owner).toBe('platform-team');
    });

    test('passes full schema validation', () => {
      const result = validateSchema(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Parameters', () => {
    test('has exactly 6 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(6);
    });

    test('first group is Component Information', () => {
      expect(template.spec.parameters[0].title).toBe('Component Information');
    });

    test('second group is AWS Configuration', () => {
      expect(template.spec.parameters[1].title).toBe('AWS Configuration');
    });

    test('has Network Configuration group', () => {
      expect(template.spec.parameters[2].title).toBe('Network Configuration');
    });

    test('has MLflow Configuration group', () => {
      expect(template.spec.parameters[3].title).toBe('MLflow Configuration');
    });

    test('has Gateway Configuration group', () => {
      expect(template.spec.parameters[4].title).toBe('Gateway Configuration');
    });

    test('last group is Repository Configuration', () => {
      expect(template.spec.parameters[5].title).toBe(
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
    });

    test('environment has dev/staging/prod', () => {
      const envProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'environment',
      );
      expect(envProperty.enum).toEqual(['dev', 'staging', 'prod']);
    });

    test('vpcId has vpc pattern', () => {
      const vpcProperty = getPropertyDefinition(
        template,
        'Network Configuration',
        'vpcId',
      );
      expect(vpcProperty).toBeDefined();
      expect(vpcProperty.pattern).toBe('^vpc-[a-z0-9]+$');
    });

    test('privateSubnetIds is required', () => {
      const networkGroup = template.spec.parameters.find(
        (g: any) => g.title === 'Network Configuration',
      );
      expect(networkGroup.required).toContain('privateSubnetIds');
    });

    test('publicSubnetIds is required', () => {
      const networkGroup = template.spec.parameters.find(
        (g: any) => g.title === 'Network Configuration',
      );
      expect(networkGroup.required).toContain('publicSubnetIds');
    });

    test('backendStoreType defaults to dynamodb', () => {
      const storeProperty = getPropertyDefinition(
        template,
        'MLflow Configuration',
        'backendStoreType',
      );
      expect(storeProperty).toBeDefined();
      expect(storeProperty.default).toBe('dynamodb');
    });

    test('containerCpu has valid options', () => {
      const cpuProperty = getPropertyDefinition(
        template,
        'Gateway Configuration',
        'containerCpu',
      );
      expect(cpuProperty).toBeDefined();
      expect(cpuProperty.enum).toContain(256);
      expect(cpuProperty.enum).toContain(512);
      expect(cpuProperty.enum).toContain(1024);
      expect(cpuProperty.enum).toContain(2048);
    });

    test('containerMemory has valid options', () => {
      const memProperty = getPropertyDefinition(
        template,
        'Gateway Configuration',
        'containerMemory',
      );
      expect(memProperty).toBeDefined();
      expect(memProperty.enum).toContain(512);
      expect(memProperty.enum).toContain(1024);
      expect(memProperty.enum).toContain(2048);
      expect(memProperty.enum).toContain(4096);
    });

    test('desiredCount has min/max bounds', () => {
      const countProperty = getPropertyDefinition(
        template,
        'Gateway Configuration',
        'desiredCount',
      );
      expect(countProperty).toBeDefined();
      expect(countProperty.minimum).toBe(1);
      expect(countProperty.maximum).toBe(10);
    });

    test('enableAutoScaling is boolean', () => {
      const scalingProperty = getPropertyDefinition(
        template,
        'Gateway Configuration',
        'enableAutoScaling',
      );
      expect(scalingProperty).toBeDefined();
      expect(scalingProperty.type).toBe('boolean');
      expect(scalingProperty.default).toBe(true);
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
      expect(template.spec.output.links.length).toBeGreaterThanOrEqual(2);
    });

    test('has ECS Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'ECS Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
