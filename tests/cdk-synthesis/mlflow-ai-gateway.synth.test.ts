/**
 * MLflow AI Gateway CDK Synthesis Tests
 *
 * Tests that CDK synth succeeds for the MLflow AI Gateway template skeleton
 * after substituting template variables with test values.
 */

import path from 'path';
import { prepareSkeleton, runCdkSynth, cleanup } from '../helpers/cdk-synth-runner';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/mlflow/ai-gateway',
);

describe('MLflow AI Gateway CDK Synthesis', () => {
  let workDir: string;
  let synthResult: Awaited<ReturnType<typeof runCdkSynth>> | null = null;

  beforeAll(async () => {
    workDir = await prepareSkeleton(TEMPLATE_DIR, {
      name: 'test-mlflow',
      description: 'Test MLflow AI Gateway for synthesis validation',
      owner: 'platform-team',
      awsRegion: 'us-east-1',
      awsAccountId: '111111111111',
      accountId: '111111111111',
      environment: 'dev',
      vpcId: 'vpc-abc123def',
      privateSubnetIds: 'subnet-aaa111,subnet-bbb222',
      publicSubnetIds: 'subnet-ccc333,subnet-ddd444',
      backendStoreType: 'dynamodb',
      artifactBucketName: '',
      containerCpu: '512',
      containerMemory: '1024',
      desiredCount: '2',
      enableAutoScaling: 'true',
      repoUrl: 'github.com?repo=test-repo&owner=test-owner',
    });
  }, 120000);

  afterAll(async () => {
    if (workDir) await cleanup(workDir);
  });

  test('cdk synth succeeds', async () => {
    synthResult = await runCdkSynth(workDir);
    expect(synthResult.exitCode).toBe(0);
  }, 120000);

  test('produces valid CloudFormation template', async () => {
    if (!synthResult) {
      synthResult = await runCdkSynth(workDir);
    }
    expect(synthResult.cfnTemplate).toBeDefined();
    expect(synthResult.cfnTemplate).not.toBeNull();
  }, 120000);

  test('CloudFormation template contains ECS resources', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const resourceTypes = Object.values(resources).map((r: any) => r.Type);
      // Should contain at least some ECS-related resources
      const hasEcsResources = resourceTypes.some(
        (t: string) =>
          t.startsWith('AWS::ECS::') ||
          t.startsWith('AWS::ElasticLoadBalancingV2::') ||
          t === 'AWS::ECR::Repository',
      );
      expect(hasEcsResources).toBe(true);
    }
  }, 120000);

  test('CloudFormation template contains IAM roles', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const iamRoles = Object.values(resources).filter(
        (r: any) => r.Type === 'AWS::IAM::Role',
      );
      expect(iamRoles.length).toBeGreaterThan(0);
    }
  }, 120000);
});
