/**
 * QnA RAG Pipeline Template Validation Tests
 *
 * Validates the QnA RAG template YAML structure, parameter groups,
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
  '../../templates/fmops/qna-rag',
);

describe('QnA RAG Pipeline Template Validation', () => {
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
      expect(template.metadata.name).toBe('genforge-qna-rag-template');
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has rag tag', () => {
      expect(template.metadata.tags).toContain('rag');
    });

    test('has opensearch tag', () => {
      expect(template.metadata.tags).toContain('opensearch');
    });

    test('has fmops tag', () => {
      expect(template.metadata.tags).toContain('fmops');
    });

    test('has correct spec.type', () => {
      expect(template.spec.type).toBe('fmops');
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

    test('has Model Configuration group', () => {
      expect(template.spec.parameters[3].title).toBe('Model Configuration');
    });

    test('has OpenSearch Configuration group', () => {
      expect(template.spec.parameters[4].title).toBe(
        'OpenSearch Configuration',
      );
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

    test('privateSubnetIds has subnet pattern', () => {
      const subnetProperty = getPropertyDefinition(
        template,
        'Network Configuration',
        'privateSubnetIds',
      );
      expect(subnetProperty).toBeDefined();
      expect(subnetProperty.pattern).toBeDefined();
    });

    test('bedrockModelId has model options', () => {
      const modelProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'bedrockModelId',
      );
      expect(modelProperty).toBeDefined();
      expect(modelProperty.enum).toBeDefined();
      expect(modelProperty.enum.length).toBeGreaterThan(0);
      expect(modelProperty.enum).toContain(
        'anthropic.claude-3-sonnet-20240229-v1:0',
      );
    });

    test('embeddingModelId has embedding model options', () => {
      const embeddingProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'embeddingModelId',
      );
      expect(embeddingProperty).toBeDefined();
      expect(embeddingProperty.enum).toContain('amazon.titan-embed-text-v1');
    });

    test('vectorDimensions has valid options', () => {
      const dimProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'vectorDimensions',
      );
      expect(dimProperty).toBeDefined();
      expect(dimProperty.enum).toContain(1536);
      expect(dimProperty.enum).toContain(1024);
    });

    test('collectionName has pattern', () => {
      const collProperty = getPropertyDefinition(
        template,
        'OpenSearch Configuration',
        'collectionName',
      );
      expect(collProperty).toBeDefined();
      expect(collProperty.pattern).toBe('^[a-z0-9-]+$');
      expect(collProperty.maxLength).toBe(32);
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

    test('has OpenSearch Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'OpenSearch Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
