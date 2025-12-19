#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { DatabaseStack } from "./lib/database-stack";
import * as dotenv from 'dotenv'
dotenv.config();
const app = new cdk.App();

new DatabaseStack(app, "DatabaseStack", {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT,
        region: process.env.CDK_DEFAULT_REGION
    }
});
