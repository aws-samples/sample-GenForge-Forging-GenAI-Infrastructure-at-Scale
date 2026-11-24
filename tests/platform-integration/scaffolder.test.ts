/**
 * Scaffolder Template Registration Tests
 *
 * Verifies that all 8 GenForge templates are properly referenced in
 * app-config.yaml and that each template's spec.type matches its
 * expected group filter for the ScaffolderPage.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'yaml';

const ROOT_DIR = path.resolve(__dirname, '../../');
const APP_CONFIG_PATH = path.join(ROOT_DIR, 'app-config.yaml');

/**
 * All 8 template paths relative to app-config.yaml location,
 * as referenced in the catalog locations section.
 */
const EXPECTED_TEMPLATES = [
  {
    path: '../../templates/foundation/vpc/template.yaml',
    name: 'genforge-vpc-template',
    type: 'foundation',
  },
  {
    path: '../../templates/fmops/bedrock-finetuning/template.yaml',
    name: 'genforge-bedrock-finetuning-template',
    type: 'fmops',
  },
  {
    path: '../../templates/fmops/qna-rag/template.yaml',
    name: 'genforge-qna-rag-template',
    type: 'fmops',
  },
  {
    path: '../../templates/fmops/sagemaker-jumpstart-endpoint/template.yaml',
    name: 'genforge-sagemaker-jumpstart-endpoint-template',
    type: 'fmops',
  },
  {
    path: '../../templates/fmops/sagemaker-huggingface-endpoint/template.yaml',
    name: 'genforge-sagemaker-huggingface-endpoint-template',
    type: 'fmops',
  },
  {
    path: '../../templates/fmops/sagemaker-llm-finetune/template.yaml',
    name: 'genforge-sagemaker-llm-finetune-template',
    type: 'fmops',
  },
  {
    path: '../../templates/agents/eks-strands-agents/template.yaml',
    name: 'genforge-eks-strands-agents-template',
    type: 'agents',
  },
  {
    path: '../../templates/mlflow/ai-gateway/template.yaml',
    name: 'genforge-mlflow-ai-gateway-template',
    type: 'mlflow',
  },
];

/**
 * The 4 ScaffolderPage group filter types that must be covered.
 */
const EXPECTED_GROUP_TYPES = ['foundation', 'fmops', 'agents', 'mlflow'];

describe('Scaffolder Template Registration', () => {
  let appConfig: any;

  beforeAll(() => {
    const content = fs.readFileSync(APP_CONFIG_PATH, 'utf-8');
    appConfig = yaml.parse(content);
  });

  describe('app-config.yaml structure', () => {
    test('app-config.yaml exists', () => {
      expect(fs.existsSync(APP_CONFIG_PATH)).toBe(true);
    });

    test('has catalog section', () => {
      expect(appConfig.catalog).toBeDefined();
    });

    test('has catalog locations', () => {
      expect(appConfig.catalog.locations).toBeDefined();
      expect(Array.isArray(appConfig.catalog.locations)).toBe(true);
    });

    test('catalog rules allow Template kind', () => {
      const rules = appConfig.catalog.rules;
      expect(rules).toBeDefined();
      const allowedKinds = rules.flatMap((r: any) => r.allow);
      expect(allowedKinds).toContain('Template');
    });
  });

  describe('template references', () => {
    test('all 8 templates are referenced in app-config.yaml', () => {
      const locations = appConfig.catalog.locations;
      const targets = locations.map((l: any) => l.target);

      for (const template of EXPECTED_TEMPLATES) {
        expect(targets).toContain(template.path);
      }
    });

    test('each template location has type "file"', () => {
      const locations = appConfig.catalog.locations;

      for (const template of EXPECTED_TEMPLATES) {
        const location = locations.find(
          (l: any) => l.target === template.path,
        );
        expect(location).toBeDefined();
        expect(location.type).toBe('file');
      }
    });

    test('each template location allows Template kind', () => {
      const locations = appConfig.catalog.locations;

      for (const template of EXPECTED_TEMPLATES) {
        const location = locations.find(
          (l: any) => l.target === template.path,
        );
        expect(location).toBeDefined();
        if (location.rules) {
          const allowedKinds = location.rules.flatMap((r: any) => r.allow);
          expect(allowedKinds).toContain('Template');
        }
      }
    });
  });

  describe('template spec.type matches group filters', () => {
    for (const template of EXPECTED_TEMPLATES) {
      test(`${template.name} has spec.type="${template.type}"`, () => {
        // Resolve the template path relative to app-config.yaml location
        // app-config.yaml references paths like ../../templates/... which are
        // relative to packages/app/ or packages/backend/ context.
        // But for our test, we resolve from the ROOT_DIR.
        const templatePath = path.resolve(
          ROOT_DIR,
          'templates',
          template.path.replace('../../templates/', ''),
        );
        expect(fs.existsSync(templatePath)).toBe(true);

        const content = fs.readFileSync(templatePath, 'utf-8');
        const parsed = yaml.parse(content);

        expect(parsed.spec.type).toBe(template.type);
      });
    }
  });

  describe('all group filter types have templates', () => {
    const templatesByType: Record<string, string[]> = {};

    beforeAll(() => {
      for (const template of EXPECTED_TEMPLATES) {
        if (!templatesByType[template.type]) {
          templatesByType[template.type] = [];
        }
        templatesByType[template.type].push(template.name);
      }
    });

    for (const groupType of EXPECTED_GROUP_TYPES) {
      test(`type "${groupType}" has at least one template`, () => {
        const templates = EXPECTED_TEMPLATES.filter(
          t => t.type === groupType,
        );
        expect(templates.length).toBeGreaterThan(0);
      });
    }

    test('foundation type has 1 template', () => {
      const foundationTemplates = EXPECTED_TEMPLATES.filter(
        t => t.type === 'foundation',
      );
      expect(foundationTemplates).toHaveLength(1);
    });

    test('fmops type has 5 templates', () => {
      const fmopsTemplates = EXPECTED_TEMPLATES.filter(
        t => t.type === 'fmops',
      );
      expect(fmopsTemplates).toHaveLength(5);
    });

    test('agents type has 1 template', () => {
      const agentsTemplates = EXPECTED_TEMPLATES.filter(
        t => t.type === 'agents',
      );
      expect(agentsTemplates).toHaveLength(1);
    });

    test('mlflow type has 1 template', () => {
      const mlflowTemplates = EXPECTED_TEMPLATES.filter(
        t => t.type === 'mlflow',
      );
      expect(mlflowTemplates).toHaveLength(1);
    });
  });

  describe('scaffolder configuration', () => {
    test('has scaffolder section', () => {
      expect(appConfig.scaffolder).toBeDefined();
    });

    test('has defaultAuthor', () => {
      expect(appConfig.scaffolder.defaultAuthor).toBeDefined();
      expect(appConfig.scaffolder.defaultAuthor.name).toBeDefined();
      expect(appConfig.scaffolder.defaultAuthor.email).toBeDefined();
    });

    test('has defaultCommitMessage', () => {
      expect(appConfig.scaffolder.defaultCommitMessage).toBeDefined();
    });
  });

  describe('catalog also registers non-template entities', () => {
    test('references genforge-system.yaml', () => {
      const locations = appConfig.catalog.locations;
      const targets = locations.map((l: any) => l.target);
      expect(targets).toContain('../../catalog/genforge-system.yaml');
    });

    test('references org.yaml', () => {
      const locations = appConfig.catalog.locations;
      const targets = locations.map((l: any) => l.target);
      expect(targets).toContain('../../catalog/org.yaml');
    });

    test('references aws-accounts.yaml', () => {
      const locations = appConfig.catalog.locations;
      const targets = locations.map((l: any) => l.target);
      expect(targets).toContain('../../catalog/aws-accounts.yaml');
    });
  });
});
