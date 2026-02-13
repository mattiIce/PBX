# Warden VoIP PBX - AWS Infrastructure

This directory contains Terraform configuration for deploying the Warden VoIP PBX system on AWS in a highly available, production-ready configuration.

## Architecture

The Terraform configuration deploys the following AWS resources:

### Network Infrastructure
- **VPC** with public and private subnets across 2 availability zones
- **Internet Gateway** for public internet access
- **Route Tables** for public and private subnets
- **Security Groups** for PBX, database, Redis, and load balancers

### Compute Resources
- **Auto Scaling Group** with 2+ EC2 instances (t3.xlarge by default)
- **Launch Template** with automated PBX setup via user-data script
- **Application Load Balancer** for HTTPS API traffic
- **Network Load Balancer** for SIP/RTP UDP traffic

### Data Storage
- **RDS PostgreSQL 16** (Multi-AZ, encrypted, automated backups)
- **ElastiCache Redis** cluster for session state (2 nodes, multi-AZ)

### Security & Secrets
- **AWS Secrets Manager** for database credentials
- **IAM Roles** with least-privilege access
- **ACM Certificate** for SSL/TLS (requires DNS validation)
- **Encrypted EBS volumes** for all instances

### Monitoring
- **CloudWatch Metrics** for system and application monitoring
- **CloudWatch Logs** for centralized logging
- **Auto Scaling Policies** based on CPU utilization

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

Create an SSH key pair in AWS:

```bash
aws ec2 create-key-pair \
  --key-name pbx-production \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/pbx-production.pem

chmod 400 ~/.ssh/pbx-production.pem
```

### 3. Terraform Installation

```bash
# Install Terraform 1.5+
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

### 4. DNS Domain (Optional)

For SSL certificate, you'll need a domain name. Update `main.tf`:

```hcl
resource "aws_acm_certificate" "pbx_cert" {
  domain_name       = "pbx.yourdomain.com"  # <-- Change this
  validation_method = "DNS"
}
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
aws_region           = "us-east-1"
environment          = "production"
ssh_key_name         = "pbx-production"
pbx_instance_count   = 2
pbx_instance_type    = "t3.xlarge"
db_instance_class    = "db.r6g.large"

# Optional: Restrict SSH access
allowed_ssh_cidr = ["1.2.3.4/32"]  # Your IP
```

### 3. Plan Deployment

```bash
terraform plan -out=tfplan
```

Review the planned changes carefully.

### 4. Deploy Infrastructure

```bash
terraform apply tfplan
```

This will take 10-15 minutes to complete.

### 5. Get Outputs

```bash
# Get load balancer DNS names
terraform output alb_dns_name
terraform output nlb_dns_name

# Get database endpoint
terraform output database_endpoint

# Get Redis endpoint
terraform output redis_endpoint
```

### 6. Configure DNS

Point your domain to the load balancer:

```bash
# Get the ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Create CNAME record in your DNS provider
# pbx.yourdomain.com CNAME $ALB_DNS
```

### 7. Validate SSL Certificate

After creating the DNS CNAME for certificate validation:

```bash
# Check certificate status
aws acm describe-certificate \
  --certificate-arn $(terraform output -raw certificate_arn) \
  --query 'Certificate.Status'
```

## Configuration

### Scaling

Adjust instance count and size in `terraform.tfvars`:

```hcl
# For 100 users, 25 concurrent calls
pbx_instance_count = 2
pbx_instance_type  = "t3.large"    # 2 vCPU, 8 GB RAM
db_instance_class  = "db.t3.medium" # 2 vCPU, 4 GB RAM

# For 500 users, 125 concurrent calls
pbx_instance_count = 3
pbx_instance_type  = "t3.xlarge"   # 4 vCPU, 16 GB RAM
db_instance_class  = "db.r6g.large" # 2 vCPU, 16 GB RAM

# For 1000+ users, 250+ concurrent calls
pbx_instance_count = 5
pbx_instance_type  = "t3.2xlarge"  # 8 vCPU, 32 GB RAM
db_instance_class  = "db.r6g.xlarge" # 4 vCPU, 32 GB RAM
```

### Multi-Region Deployment

For disaster recovery, deploy in a second region:

```bash
# Deploy to us-west-2 for DR
cd terraform/aws

# Create separate workspace
terraform workspace new us-west-2

# Update region in tfvars
echo 'aws_region = "us-west-2"' > terraform.tfvars

# Deploy
terraform plan
terraform apply
```

### Cost Optimization

**Use Spot Instances for non-production**:

Modify `aws_launch_template` in `main.tf`:

```hcl
resource "aws_launch_template" "pbx" {
  # ... existing config ...
  
  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price = "0.10"  # Max price per hour
    }
  }
}
```

**Use Reserved Instances for production**:

Purchase Reserved Instances for cost savings (up to 72% off):

```bash
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id <offering-id> \
  --instance-count 2
```

## Monitoring

### CloudWatch Dashboards

Access CloudWatch:

```bash
# Open CloudWatch in AWS Console
echo "https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
```

### Application Logs

```bash
# View application logs
aws logs tail /pbx/production/application --follow

# View user-data logs (instance startup)
aws logs tail /pbx/production/user-data --follow
```

### Metrics

Key metrics to monitor:
- `PBX/production/CPU_IDLE` - CPU utilization
- `PBX/production/MEM_USED` - Memory usage
- `PBX/production/DISK_USED` - Disk usage
- `AWS/RDS/CPUUtilization` - Database CPU
- `AWS/ElastiCache/CPUUtilization` - Redis CPU

## Backup and Recovery

### Database Backups

Automated daily backups with 30-day retention:

```bash
# List available backups
aws rds describe-db-snapshots \
  --db-instance-identifier pbx-db-production

# Restore from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier pbx-db-restored \
  --db-snapshot-identifier <snapshot-id>
```

### Manual Snapshot

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier pbx-db-production \
  --db-snapshot-identifier pbx-manual-snapshot-$(date +%Y%m%d)
```

## Maintenance

### Updating PBX Application

Rolling update procedure:

```bash
# SSH to instances and update (done automatically by ASG)
# Or trigger ASG instance refresh

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name pbx-asg-production \
  --preferences MinHealthyPercentage=50
```

### Database Maintenance

Apply updates during maintenance window (Sunday 4-5 AM UTC by default):

```bash
# Modify maintenance window
aws rds modify-db-instance \
  --db-instance-identifier pbx-db-production \
  --preferred-maintenance-window "sun:04:00-sun:05:00"
```

## Troubleshooting

### Instance Not Starting

```bash
# Check user-data logs
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names pbx-asg-production \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

aws logs tail /pbx/production/user-data --follow --log-stream-name $INSTANCE_ID
```

### Database Connection Issues

```bash
# Check database status
aws rds describe-db-instances \
  --db-instance-identifier pbx-db-production \
  --query 'DBInstances[0].DBInstanceStatus'

# Check security group
aws ec2 describe-security-groups \
  --group-ids <database-security-group-id>
```

### Load Balancer Health Checks Failing

```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# SSH to instance and check service
ssh -i ~/.ssh/pbx-production.pem ubuntu@<instance-ip>
sudo systemctl status pbx
curl http://localhost:8080/health
```

## Cleanup

### Destroy Infrastructure

**WARNING**: This will delete all resources including data!

```bash
# Disable deletion protection
terraform apply -var="enable_deletion_protection=false"

# Destroy all resources
terraform destroy

# Confirm with: yes
```

### Partial Cleanup

Keep database but remove compute:

```bash
# Target specific resources
terraform destroy -target=aws_autoscaling_group.pbx_asg
terraform destroy -target=aws_lb.pbx_alb
terraform destroy -target=aws_lb.pbx_nlb
```

## Cost Estimate

### Monthly Costs (us-east-1)

**Small (100 users)**:
- EC2 (2 x t3.large): $120
- RDS (db.t3.medium): $90
- ElastiCache (2 x cache.t3.micro): $25
- Data transfer: $50
- Load balancers: $40
- **Total: ~$325/month**

**Medium (500 users)**:
- EC2 (3 x t3.xlarge): $360
- RDS (db.r6g.large): $240
- ElastiCache (2 x cache.r6g.large): $180
- Data transfer: $200
- Load balancers: $40
- **Total: ~$1,020/month**

**Large (1000+ users)**:
- EC2 (5 x t3.2xlarge): $1,200
- RDS (db.r6g.xlarge): $480
- ElastiCache (3 x cache.r6g.large): $270
- Data transfer: $500
- Load balancers: $60
- **Total: ~$2,510/month**

> **Note**: Use AWS Cost Calculator for precise estimates: https://calculator.aws/

## Security Best Practices

1. **Enable MFA** on AWS account
2. **Use IAM roles** instead of access keys where possible
3. **Rotate credentials** regularly
4. **Enable CloudTrail** for audit logging
5. **Use VPC Flow Logs** for network monitoring
6. **Enable GuardDuty** for threat detection
7. **Regular security scans** with AWS Inspector
8. **Keep software updated** via auto-scaling refresh

## Support

- **Documentation**: See main repository README
- **Issues**: GitHub Issues
- **Security**: Report to security@example.com
- **Enterprise**: Contact for professional support

## License

MIT License - See LICENSE file in repository root

---
