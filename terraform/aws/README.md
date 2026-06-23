# Warden VoIP PBX - AWS Infrastructure

This directory contains a Terraform **starting template** for deploying the Warden VoIP PBX
system on AWS. The current `main.tf` is intentionally simplified: it declares the provider,
the input variables, and a small set of outputs. It is meant to be extended into a full,
production-ready configuration (see [Roadmap](#roadmap-planned-infrastructure)).

> **Note**: `main.tf` is a skeleton. Its `instructions`, `alb_dns_name`, and `nlb_dns_name`
> outputs reference resources (load balancers, RDS, ElastiCache, Secrets Manager, etc.) that
> are **not yet defined** in this template. You must add those resources before
> `terraform plan` / `terraform apply` will succeed.

## What main.tf Currently Provides

### Provider

- `hashicorp/aws` `~> 5.0`
- `hashicorp/random` `~> 3.5`
- Required Terraform version: `>= 1.9.0`
- Default tags applied to all resources: `Project`, `Environment`, `ManagedBy`

### Input Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `aws_region` | string | `us-east-1` | AWS region |
| `environment` | string | `production` | Environment (dev/staging/production) |
| `vpc_cidr` | string | `10.0.0.0/16` | VPC CIDR block |
| `pbx_instance_count` | number | `2` | Number of PBX instances |
| `pbx_instance_type` | string | `t3.xlarge` | EC2 instance type |
| `db_instance_class` | string | `db.t3.medium` | RDS instance class |
| `ssh_key_name` | string | *(required)* | SSH key pair name |
| `allowed_ssh_cidr` | list(string) | *(required)* | CIDR blocks allowed to SSH. Must not be `0.0.0.0/0` (enforced by a validation rule). |

### Outputs

| Output | Description |
|--------|-------------|
| `instructions` | Post-deployment instructions (references resources to be added) |
| `alb_dns_name` | ALB DNS name for the HTTPS API |
| `nlb_dns_name` | NLB DNS name for SIP/RTP |

There are no `database_endpoint`, `redis_endpoint`, or `certificate_arn` outputs yet — those
are part of the [roadmap](#roadmap-planned-infrastructure).

## Prerequisites

### 1. AWS Account and Credentials

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 2. SSH Key Pair

Create an SSH key pair in AWS (its name is passed via the `ssh_key_name` variable):

```bash
aws ec2 create-key-pair \
  --key-name pbx-production \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/pbx-production.pem

chmod 400 ~/.ssh/pbx-production.pem
```

### 3. Terraform Installation

```bash
# Install Terraform 1.9+ (required by main.tf)
wget https://releases.hashicorp.com/terraform/1.9.0/terraform_1.9.0_linux_amd64.zip
unzip terraform_1.9.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform/aws
terraform init
```

### 2. Create Variables File

Create `terraform.tfvars`:

```hcl
aws_region         = "us-east-1"
environment        = "production"
ssh_key_name       = "pbx-production"
pbx_instance_count = 2
pbx_instance_type  = "t3.xlarge"
db_instance_class  = "db.t3.medium"

# Required: restrict SSH access (0.0.0.0/0 is rejected by validation)
allowed_ssh_cidr = ["1.2.3.4/32"]  # Your IP
```

### 3. Extend the Template

Before planning, add the AWS resources you need (VPC, security groups, RDS, ElastiCache, ACM,
launch template, autoscaling group, load balancers, etc.). See
[Roadmap](#roadmap-planned-infrastructure) for the intended end state.

### 4. Plan and Apply

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

### 5. Read the Outputs

Once the corresponding resources exist, the template exposes:

```bash
terraform output alb_dns_name
terraform output nlb_dns_name
terraform output instructions
```

## Roadmap: Planned Infrastructure

The following resources are **not yet implemented** in `main.tf`. They represent the intended
production architecture and the work needed to grow this template into a complete deployment.

### Network Infrastructure
- **VPC** with public and private subnets across 2 availability zones
- **Internet Gateway** for public internet access
- **Route Tables** for public and private subnets
- **Security Groups** for PBX, database, Redis, and load balancers

### Compute Resources
- **Launch Template** with automated PBX setup via a user-data script
- **Auto Scaling Group** with 2+ EC2 instances (`t3.xlarge` by default)
- **Application Load Balancer** for HTTPS API traffic
- **Network Load Balancer** for SIP/RTP UDP traffic

### Data Storage
- **RDS PostgreSQL 17** (Multi-AZ, encrypted, automated backups)
- **ElastiCache Redis** cluster for session state (multi-AZ)

### Security & Secrets
- **ACM Certificate** for SSL/TLS (requires DNS validation)
- **AWS Secrets Manager** for database credentials
- **IAM Roles** with least-privilege access
- **Encrypted EBS volumes** for all instances

### Monitoring
- **CloudWatch Metrics** for system and application monitoring
- **CloudWatch Logs** for centralized logging
- **Auto Scaling Policies** based on CPU utilization

### Additional Outputs
- `database_endpoint` — RDS endpoint address
- `redis_endpoint` — ElastiCache configuration endpoint
- `certificate_arn` — ACM certificate ARN

## Support

- **Documentation**: See the main repository README, and [docs/PLANNED_FEATURES.md](../../docs/PLANNED_FEATURES.md) for the consolidated roadmap
- **Issues**: GitHub Issues

## License

MIT License - See the LICENSE file in the repository root
