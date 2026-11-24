/**
 * EKS Strands AI Agents Template Validation Tests
 *
 * Validates the Strands AI Agents on EKS template YAML structure,
 * parameter groups, steps, and skeleton files. This template has
 * additional skeleton files for the agent application code.
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
  '../../templates/agents/eks-strands-agents',
);

describe('EKS Strands AI Agents Template Validation', () => {
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
        'genforge-eks-strands-agents-template',
      );
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has eks tag', () => {
      expect(template.metadata.tags).toContain('eks');
    });

    test('has strands tag', () => {
      expect(template.metadata.tags).toContain('strands');
    });

    test('has agents tag', () => {
      expect(template.metadata.tags).toContain('agents');
    });

    test('has correct spec.type', () => {
      expect(template.spec.type).toBe('agents');
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
    test('has exactly 5 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(5);
    });

    test('first group is Component Information', () => {
      expect(template.spec.parameters[0].title).toBe('Component Information');
    });

    test('second group is AWS Configuration', () => {
      expect(template.spec.parameters[1].title).toBe('AWS Configuration');
    });

    test('has EKS Configuration group', () => {
      expect(template.spec.parameters[2].title).toBe('EKS Configuration');
    });

    test('has Agent Configuration group', () => {
      expect(template.spec.parameters[3].title).toBe('Agent Configuration');
    });

    test('last group is Repository Configuration', () => {
      expect(template.spec.parameters[4].title).toBe(
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

    test('eksClusterName is a required string', () => {
      const clusterProperty = getPropertyDefinition(
        template,
        'EKS Configuration',
        'eksClusterName',
      );
      expect(clusterProperty).toBeDefined();
      expect(clusterProperty.type).toBe('string');
      const eksGroup = template.spec.parameters.find(
        (g: any) => g.title === 'EKS Configuration',
      );
      expect(eksGroup.required).toContain('eksClusterName');
    });

    test('ecrRepoName has default value', () => {
      const ecrProperty = getPropertyDefinition(
        template,
        'EKS Configuration',
        'ecrRepoName',
      );
      expect(ecrProperty).toBeDefined();
      expect(ecrProperty.type).toBe('string');
      expect(ecrProperty.default).toBe('strands-agent');
    });

    test('bedrockModelId has Bedrock model options', () => {
      const modelProperty = getPropertyDefinition(
        template,
        'Agent Configuration',
        'bedrockModelId',
      );
      expect(modelProperty).toBeDefined();
      expect(modelProperty.enum).toContain(
        'anthropic.claude-3-sonnet-20240229-v1:0',
      );
      expect(modelProperty.enum).toContain(
        'anthropic.claude-3-haiku-20240307-v1:0',
      );
      expect(modelProperty.enum).toContain('amazon.titan-text-express-v1');
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
    test('has all required common skeleton files', () => {
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

    test('has agent application files', () => {
      validateSkeletonFiles(TEMPLATE_DIR, [
        'skeleton/agent/agent.py',
        'skeleton/agent/Dockerfile',
        'skeleton/agent/requirements.txt',
      ]);
    });
  });

  describe('Output', () => {
    test('has output links', () => {
      expect(template.spec.output.links.length).toBeGreaterThanOrEqual(2);
    });

    test('has EKS Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'EKS Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
