/**
 * VPC Foundation CDK Synthesis Tests
 *
 * Tests that CDK synth succeeds for the VPC template skeleton after
 * substituting template variables with test values.
 */

import path from 'path';
import { prepareSkeleton, runCdkSynth, cleanup } from '../helpers/cdk-synth-runner';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/foundation/vpc',
);

describe('VPC Foundation CDK Synthesis', () => {
  let workDir: string;
  let synthResult: Awaited<ReturnType<typeof runCdkSynth>> | null = null;

  beforeAll(async () => {
    workDir = await prepareSkeleton(TEMPLATE_DIR, {
      name: 'test-vpc',
      description: 'Test VPC for synthesis validation',
      owner: 'platform-team',
      awsRegion: 'us-east-1',
      accountId: '111111111111',
      environment: 'dev',
      vpcCidr: '10.0.0.0/16',
      availabilityZones: '2',
      enableNatGateway: 'true',
      singleNatGateway: 'true',
      enableVpcEndpoints: 'true',
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

  test('CloudFormation template contains VPC resource', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const vpcResources = Object.values(resources).filter(
        (r: any) => r.Type === 'AWS::EC2::VPC',
      );
      expect(vpcResources.length).toBeGreaterThan(0);
    }
  }, 120000);

  test('CloudFormation template contains subnet resources', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const subnetResources = Object.values(resources).filter(
        (r: any) => r.Type === 'AWS::EC2::Subnet',
      );
      // 2 AZs x 3 subnet types (public, private, isolated) = 6 subnets
      expect(subnetResources.length).toBeGreaterThanOrEqual(6);
    }
  }, 120000);

  test('CloudFormation template has outputs', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const outputs = synthResult.cfnTemplate.Outputs || {};
      expect(Object.keys(outputs).length).toBeGreaterThan(0);
    }
  }, 120000);
});
