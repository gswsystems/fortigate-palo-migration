# Quick Start Guide - FortiGate to Palo Alto Migration

## Prerequisites Check

```bash
# Python version (requires 3.7+)
python3 --version

# Install dependencies
pip3 install -r requirements.txt
```

## Step 1: FortiGate API Setup

### Generate API Key

1. Login to FortiGate: `https://your-fortigate-ip`
2. Navigate: **System > Administrators**
3. Click **Create New > REST API Admin**
4. Configure:
   ```
   Username: migration_api
   Administrator Profile: super_admin
   Trusted Hosts: <your-ip-address>
   ```
5. Click **OK** and copy the API key immediately

### Test API Access

```bash
# Test connection
curl -k -H "Authorization: Bearer YOUR_API_KEY" \
  "https://your-fortigate-ip/api/v2/cmdb/system/global"
```

## Step 2: Run Migration

### Option A: Quick Migration (Single Command)

```bash
python3 fortigate_palo_converter.py \
  --host your-fortigate-ip \
  --api-key YOUR_API_KEY \
  --output migration.tf
```

### Option B: Production Migration (Full Options)

```bash
python3 fortigate_palo_converter.py \
  --host firewall.company.com \
  --api-key YOUR_API_KEY \
  --vdom production \
  --device-group "Production-DG" \
  --template "Production-Template" \
  --output prod_migration.tf \
  --save-json debug.json
```

### Option C: Using Environment Variables

```bash
# Set environment
export FORTIGATE_HOST="firewall.company.com"
export FORTIGATE_API_KEY="your-api-key"
export FORTIGATE_VDOM="root"

# Run migration
python3 fortigate_palo_converter.py -o migration.tf
```

## Step 3: Review Output

```bash
# View generated Terraform
cat migration.tf

# Check for manual migration notes
grep "MANUAL" migration.tf

# Count resources
grep 'resource "panos_' migration.tf | wc -l
```

## Step 4: Prepare Palo Alto

### Configure Terraform Provider

Create `provider.tf`:

```hcl
terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 1.13"
    }
  }
}

provider "panos" {
  hostname = var.panos_hostname
  username = var.panos_username
  password = var.panos_password
}
```

Create `variables.tf`:

```hcl
variable "panos_hostname" {
  description = "Palo Alto Panorama/Firewall hostname"
  type        = string
}

variable "panos_username" {
  description = "Palo Alto admin username"
  type        = string
  sensitive   = true
}

variable "panos_password" {
  description = "Palo Alto admin password"
  type        = string
  sensitive   = true
}
```

Create `terraform.tfvars`:

```hcl
panos_hostname = "panorama.company.com"
panos_username = "admin"
panos_password = "your-password"
```

## Step 5: Initialize and Plan

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Review planned changes
terraform plan -out=migration.plan

# Count resources to be created
terraform plan | grep "Plan:"
```

## Step 6: Apply Migration

```bash
# Apply with auto-approve (be careful!)
terraform apply migration.plan

# Or apply with confirmation
terraform apply

# Save state
terraform state list > deployed_resources.txt
```

## Step 7: Verification

### Verify in Palo Alto

```bash
# Via Panorama/Firewall GUI:
# - Objects > Address
# - Objects > Service
# - Policies > Security
# - Policies > NAT

# Or via CLI:
ssh admin@panorama.company.com
show config merged | match "address "
show config merged | match "service "
show config merged | match "security rules"
```

### Test Connectivity

```bash
# Test security policy
# From Palo Alto CLI:
test security-policy-match \
  source 192.168.1.10 \
  destination 10.0.0.10 \
  protocol 6 \
  destination-port 443

# Test NAT policy
test nat-policy-match \
  source 192.168.1.10 \
  destination 8.8.8.8 \
  protocol 6 \
  destination-port 53
```

## Common Issues

### Issue 1: SSL Certificate Error

```bash
# Solution: Disable SSL verification
python3 fortigate_palo_converter.py \
  --host firewall.local \
  --api-key KEY \
  --no-verify-ssl
```

### Issue 2: Authentication Failed

```bash
# Verify API key
curl -k -H "Authorization: Bearer KEY" \
  "https://firewall.local/api/v2/monitor/system/status"

# Check trusted hosts
curl -k -H "Authorization: Bearer KEY" \
  "https://firewall.local/api/v2/cmdb/system/api-user"
```

### Issue 3: Missing Objects

```bash
# Enable debug output
python3 fortigate_palo_converter.py \
  --save-json debug.json \
  ...

# Analyze JSON
jq '.policies[] | select(.name == "policy_name")' debug.json
```

### Issue 4: Terraform Provider Errors

```bash
# Update provider
terraform init -upgrade

# Verify provider version
terraform version

# Check provider documentation
terraform providers
```

## Post-Migration Tasks

### 1. Security Profiles (Manual)

Create security profiles in Palo Alto:
- Antivirus profiles
- Anti-Spyware profiles
- Vulnerability Protection
- URL Filtering profiles
- File Blocking profiles
- WildFire Analysis profiles

### 2. Application-ID Migration (Manual)

Replace port-based policies with App-ID:
```hcl
# Change from:
services = ["service-tcp-443"]

# To:
applications = ["ssl", "web-browsing"]
services     = ["application-default"]
```

### 3. SSL Decryption (Manual)

Configure decryption policies for HTTPS inspection:
```hcl
resource "panos_decryption_rule_group" "ssl_decrypt" {
  # Configure SSL/TLS decryption
}
```

### 4. Commit Changes

```bash
# Via GUI:
# Commit > Commit to Panorama
# Commit > Push to Devices

# Via Terraform:
# Already committed during apply
```

## Maintenance

### Update Configuration

```bash
# After making changes to FortiGate
python3 fortigate_palo_converter.py ...

# Review differences
terraform plan

# Apply updates
terraform apply
```

### Backup State

```bash
# Backup Terraform state
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d)

# Export Palo Alto config
# Via GUI: Device > Setup > Operations > Export
```

### Rollback

```bash
# Via Terraform
terraform destroy

# Or restore previous state
mv terraform.tfstate.backup.YYYYMMDD terraform.tfstate
terraform apply
```

## Success Checklist

- [ ] FortiGate API key generated and tested
- [ ] Migration script executed successfully
- [ ] Terraform configuration validated
- [ ] All address objects created
- [ ] All service objects created
- [ ] Security policies deployed
- [ ] NAT policies deployed
- [ ] Zone assignments verified
- [ ] Routing configuration applied
- [ ] Security profiles configured (manual)
- [ ] Policies tested and verified
- [ ] Documentation updated
- [ ] State file backed up

## Support Resources

- **FortiGate API Docs**: https://docs.fortinet.com/document/fortigate/latest/rest-api-reference
- **Palo Alto Terraform Provider**: https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs
- **Terraform Docs**: https://www.terraform.io/docs
- **Script Repository**: Check README.md for detailed documentation

## Need Help?

1. Check the detailed README.md
2. Review debug JSON output (`--save-json`)
3. Validate API connectivity
4. Review Terraform plan output
5. Check Palo Alto logs for errors
