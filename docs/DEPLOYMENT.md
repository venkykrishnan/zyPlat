# Deployment Guide

This document describes how to deploy zyPlat to production with **code quality gates** that prevent deployment if checks fail.

## Overview

**Code Quality Gates:**
- ✅ Black (formatting check)
- ✅ Ruff (linting)
- ✅ mypy (type checking)
- ✅ pytest (tests with PostgreSQL)

**Deployment Targets:**
1. **Render** - Platform-as-a-Service (easiest)
2. **AWS ECS Fargate** - Containerized deployment (more control)

---

## Option 1: Deploy to Render

### Prerequisites

1. GitHub repository with code
2. Render account (https://render.com)
3. PostgreSQL database (Render provides this)

### Setup Steps

#### 1. Connect GitHub to Render

1. Go to https://dashboard.render.com
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically

#### 2. Configure Environment Variables

Render will automatically:
- Create PostgreSQL database
- Set `DATABASE_URL` environment variable
- Connect backend to database

#### 3. Code Quality Gates (Automatic)

The `render.yaml` buildCommand includes gates:

```yaml
buildCommand: |
  # Install dependencies
  pip install -r backend/requirements-dev.txt
  
  # CODE QUALITY GATES (deployment fails if these fail)
  black --check backend/ cli/ || exit 1
  ruff check backend/ cli/ || exit 1
  mypy backend/app/ cli/zyplat_cli/ || exit 1
  
  # Run migrations
  cd backend && alembic upgrade head
```

**If any check fails → Deployment is blocked! ❌**

#### 4. Deploy

```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

Render auto-deploys when you push to `main`.

### Monitoring Deployment

1. Go to https://dashboard.render.com
2. Click on "zyplat-backend" service
3. View "Logs" tab to see:
   - ✅ Black check passed
   - ✅ Ruff check passed
   - ✅ mypy check passed
   - ✅ Migrations applied
   - ✅ Service started

### Manual Deploy

To trigger a manual deployment:

```bash
# From Render dashboard
Services → zyplat-backend → "Manual Deploy" → Deploy latest commit
```

### GitHub Actions Integration (Optional)

Enable GitHub Actions to run checks **before** Render deploys:

1. GitHub will run checks on PR
2. Merge only if checks pass
3. Render auto-deploys after merge

---

## Option 2: Deploy to AWS ECS Fargate

### Prerequisites

1. AWS Account
2. AWS CLI configured
3. GitHub repository
4. ECR repository created
5. ECS cluster created

### Architecture

```
GitHub (main) → GitHub Actions (gates) → ECR → ECS Fargate
                     ↓
                 Checks:
                 - black
                 - ruff  
                 - mypy
                 - pytest
```

### Setup Steps

#### 1. Create AWS Resources

```bash
# Create ECR repository
aws ecr create-repository --repository-name zyplat-backend

# Create ECS cluster
aws ecs create-cluster --cluster-name zyplat-cluster

# Create task definition (see task-definition.json below)
# Create ECS service
```

#### 2. Configure GitHub Secrets

Go to GitHub → Settings → Secrets and variables → Actions

Add these secrets:

```
AWS_ACCESS_KEY_ID        = <your-aws-access-key>
AWS_SECRET_ACCESS_KEY    = <your-aws-secret-key>
AWS_REGION               = us-east-1  (or your region)
DATABASE_URL             = postgresql://user:pass@host:5432/db
```

#### 3. Create Task Definition

Create `task-definition.json`:

```json
{
  "family": "zyplat-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "zyplat-backend",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/zyplat-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@host:5432/db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/zyplat-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register it:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 4. Create ECS Service

```bash
aws ecs create-service \
  --cluster zyplat-cluster \
  --service-name zyplat-backend-service \
  --task-definition zyplat-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### 5. Code Quality Gates (Automatic via GitHub Actions)

The `.github/workflows/deploy-ecs.yml` workflow has **3 jobs**:

1. **code-quality** (GATE)
   - Runs black, ruff, mypy
   - **Fails deployment if checks fail**

2. **test** (GATE)
   - Runs pytest with PostgreSQL
   - **Fails deployment if tests fail**

3. **build-and-push** (only if gates pass)
   - Builds Docker image
   - Pushes to ECR

4. **deploy-ecs** (only if build succeeds)
   - Runs migrations
   - Deploys to ECS

**If any gate fails → Deployment is blocked! ❌**

#### 6. Deploy

```bash
git add .
git commit -m "Deploy to ECS"
git push origin main
```

GitHub Actions will:
1. ✅ Run code quality checks
2. ✅ Run tests
3. ✅ Build Docker image
4. ✅ Push to ECR
5. ✅ Deploy to ECS

### Monitoring Deployment

```bash
# View GitHub Actions
https://github.com/<user>/zyPlat/actions

# View ECS deployment
aws ecs describe-services \
  --cluster zyplat-cluster \
  --services zyplat-backend-service

# View logs
aws logs tail /ecs/zyplat-backend --follow
```

### Manual Deploy Trigger

To manually trigger deployment:

```bash
# From GitHub
Actions → Deploy to AWS ECS Fargate → Run workflow
```

---

## Comparison: Render vs AWS ECS Fargate

| Feature | Render | AWS ECS Fargate |
|---------|--------|-----------------|
| **Setup Complexity** | ⭐ Easy (5 min) | ⭐⭐⭐ Complex (30+ min) |
| **Code Quality Gates** | ✅ In render.yaml | ✅ In GitHub Actions |
| **Auto-deploy on merge** | ✅ Built-in | ✅ Via GitHub Actions |
| **Cost** | $7-25/month | ~$10-30/month |
| **Database** | ✅ Managed PostgreSQL | ❌ Need RDS separately |
| **Scaling** | ✅ Auto-scale | ✅ Auto-scale (more config) |
| **Custom domain** | ✅ Easy | ✅ Via ALB/Route53 |
| **Logs** | ✅ Built-in dashboard | ✅ CloudWatch |
| **Control** | ⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full control |

**Recommendation:**
- **Start with Render** (easier, faster)
- **Move to ECS** later if you need more control

---

## Testing Code Quality Gates Locally

Before pushing, test gates locally:

```bash
# Run all checks
make check

# Auto-fix issues
make fix

# Run tests
make test

# If all pass ✅ → safe to deploy
```

---

## Rollback

### Render

1. Go to dashboard → zyplat-backend
2. Click "Rollbacks"
3. Select previous successful deploy
4. Click "Rollback to this version"

### AWS ECS

```bash
# List previous task definitions
aws ecs list-task-definitions --family-prefix zyplat-backend

# Update service to previous version
aws ecs update-service \
  --cluster zyplat-cluster \
  --service zyplat-backend-service \
  --task-definition zyplat-backend:3  # Previous version
```

---

## Troubleshooting

### Deployment Failed: Code Quality Check

**Symptom:** Build fails with "black check failed" or "ruff check failed"

**Fix:**
```bash
# Locally
make fix
git add .
git commit -m "Fix code quality issues"
git push origin main
```

### Deployment Failed: Tests

**Symptom:** Tests fail in CI

**Fix:**
```bash
# Run tests locally
make test

# Fix failing tests
git commit -am "Fix tests"
git push origin main
```

### Deployment Failed: Migration Error

**Symptom:** `alembic upgrade head` fails

**Fix:**
```bash
# Check migration locally
cd backend
alembic upgrade head

# If migration is broken, fix it
alembic downgrade -1
alembic revision --autogenerate -m "Fix migration"
git commit -am "Fix migration"
git push origin main
```

---

## Next Steps

1. ✅ Choose deployment target (Render or ECS)
2. ✅ Set up platform (follow setup steps above)
3. ✅ Push to `main` → Auto-deploy with gates
4. ✅ Monitor deployment logs
5. ✅ Verify `/health` endpoint is responding

**Code quality is now a deployment gate! 🎉**
