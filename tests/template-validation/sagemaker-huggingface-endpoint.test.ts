/**
 * SageMaker HuggingFace Endpoint Template Validation Tests
 *
 * Validates the SageMaker HuggingFace Endpoint template YAML structure,
 * parameter groups, steps, and skeleton files.
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
  '../../templates/fmops/sagemaker-huggingface-endpoint',
);

describe('SageMaker HuggingFace Endpoint Template Validation', () => {
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
        'genforge-sagemaker-huggingface-endpoint-template',
      );
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has sagemaker tag', () => {
      expect(template.metadata.tags).toContain('sagemaker');
    });

    test('has huggingface tag', () => {
      expect(template.metadata.tags).toContain('huggingface');
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
    test('has exactly 5 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(5);
    });

    test('first group is Component Information', () => {
      expect(template.spec.parameters[0].title).toBe('Component Information');
    });

    test('second group is AWS Configuration', () => {
      expect(template.spec.parameters[1].title).toBe('AWS Configuration');
    });

    test('has Model Configuration group', () => {
      expect(template.spec.parameters[2].title).toBe('Model Configuration');
    });

    test('has Container Configuration group', () => {
      expect(template.spec.parameters[3].title).toBe(
        'Container Configuration',
      );
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

    test('huggingfaceModelId is a string', () => {
      const modelProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'huggingfaceModelId',
      );
      expect(modelProperty).toBeDefined();
      expect(modelProperty.type).toBe('string');
      expect(modelProperty.default).toBe(
        'mistralai/Mistral-7B-Instruct-v0.2',
      );
    });

    test('taskType has valid options', () => {
      const taskProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'taskType',
      );
      expect(taskProperty).toBeDefined();
      expect(taskProperty.enum).toContain('text-generation');
      expect(taskProperty.enum).toContain('text-classification');
      expect(taskProperty.enum).toContain('question-answering');
      expect(taskProperty.enum).toContain('summarization');
    });

    test('instanceType has GPU options', () => {
      const instanceProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'instanceType',
      );
      expect(instanceProperty).toBeDefined();
      expect(instanceProperty.enum).toContain('ml.g5.xlarge');
    });

    test('tgiVersion has version options', () => {
      const tgiProperty = getPropertyDefinition(
        template,
        'Container Configuration',
        'tgiVersion',
      );
      expect(tgiProperty).toBeDefined();
      expect(tgiProperty.enum).toContain('2.3.1');
      expect(tgiProperty.enum).toContain('2.2.0');
      expect(tgiProperty.enum).toContain('2.0.1');
    });

    test('quantization has valid options', () => {
      const quantProperty = getPropertyDefinition(
        template,
        'Container Configuration',
        'quantization',
      );
      expect(quantProperty).toBeDefined();
      expect(quantProperty.enum).toContain('none');
      expect(quantProperty.enum).toContain('bitsandbytes-nf4');
      expect(quantProperty.enum).toContain('bitsandbytes-fp4');
      expect(quantProperty.enum).toContain('gptq');
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

    test('has SageMaker Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'SageMaker Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
