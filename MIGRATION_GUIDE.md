# FortiGate to Palo Alto Migration Guide

A step-by-step guide to migrating your FortiGate firewall configuration to Palo Alto Networks using this toolkit and Terraform. This guide assumes basic familiarity with firewalls but does not require prior Terraform or API experience.

---

## Table of Contents

1. [Overview](#1-overview)
2. [What Gets Migrated](#2-what-gets-migrated)
3. [Prerequisites](#3-prerequisites)
4. [Phase 1: Prepare Your FortiGate](#4-phase-1-prepare-your-fortigate)
5. [Phase 2: Prepare Your Workstation](#5-phase-2-prepare-your-workstation)
6. [Phase 3: Run the Migration Script](#6-phase-3-run-the-migration-script)
7. [Phase 4: Understand the Output](#7-phase-4-understand-the-output)
8. [Phase 5: Prepare Palo Alto for Terraform](#8-phase-5-prepare-palo-alto-for-terraform)
9. [Phase 6: Review the Terraform Plan](#9-phase-6-review-the-terraform-plan)
10. [Phase 7: Apply the Configuration](#10-phase-7-apply-the-configuration)
11. [Phase 8: Manual Configuration Tasks](#11-phase-8-manual-configuration-tasks)
12. [Phase 9: Validate the Migration](#12-phase-9-validate-the-migration)
13. [Phase 10: Cutover](#13-phase-10-cutover)
14. [Rollback Procedures](#14-rollback-procedures)
15. [Troubleshooting](#15-troubleshooting)
16. [Appendix A: Terraform Concepts for Firewall Engineers](#appendix-a-terraform-concepts-for-firewall-engineers)
17. [Appendix B: FortiGate to Palo Alto Terminology Map](#appendix-b-fortigate-to-palo-alto-terminology-map)
18. [Appendix C: What Cannot Be Automated](#appendix-c-what-cannot-be-automated)

---

## 1. Overview

This toolkit reads your FortiGate configuration via its REST API and produces a Terraform file that, when applied, creates the equivalent configuration on a Palo Alto Networks firewall or Panorama.

**How it works:**

```
FortiGate REST API  -->  Migration Script  -->  Terraform (.tf file)  -->  Palo Alto / Panorama
```

There are two scripts:

| Script | Use Case |
|--------|----------|
| `fortigate_palo_converter.py` | Core migration: addresses, services, policies, NAT, routes |
| `fortigate_palo_enhanced_main.py` | Everything above **plus** IPv6, VPN worksheets, routing analysis, security profile analysis, and a migration report |

**Recommendation:** Use the enhanced script (`fortigate_palo_enhanced_main.py`) with the `--enhanced` and `--report` flags for the most complete output.

---

## 2. What Gets Migrated

### Fully Automated (~80%)

These items are converted directly into Terraform resources and will be created on the Palo Alto automatically:

| FortiGate | Palo Alto Equivalent | Terraform Resource |
|-----------|---------------------|--------------------|
| Address objects (IP, range, FQDN, wildcard) | Address objects | `panos_address` |
| Address groups | Address groups | `panos_address_group` |
| Service objects (TCP/UDP) | Service objects | `panos_service` |
| Service groups | Service groups | `panos_service_group` |
| Firewall policies (allow/deny) | Security rules | `panos_security_policy_rules` |
| NAT with IP pools (source NAT) | NAT rules | `panos_nat_policy_rules` |
| Virtual IPs (destination NAT / port forwarding) | NAT rules | `panos_nat_policy_rules` |
| IP pools | Address objects (ip-range) | `panos_address` |
| Static routes | Static routes | `panos_virtual_router_static_route_ipv4` |
| Zones | Zones | `panos_zone` |

### Guided Manual (~15%)

These items are **analysed and documented** but require manual configuration. The enhanced migration report gives you step-by-step instructions:

- IPsec VPN tunnels (full parameter worksheets provided)
- OSPF and BGP routing protocols
- Security profiles (antivirus, IPS, URL filtering)
- SSL VPN configuration
- User authentication (RADIUS, LDAP, local users)
- SSL/TLS inspection profiles

### Not Directly Translatable (~5%)

These features are architecturally different between platforms and require redesign:

- FortiGuard subscriptions (replaced by Palo Alto Threat Prevention, WildFire, URL Filtering subscriptions)
- Security Fabric (replaced by Panorama management)
- SD-WAN (requires Prisma SD-WAN or manual policy-based routing)
- HA configuration (platform-specific setup)

---

## 3. Prerequisites

### What You Need

| Item | Details |
|------|---------|
| **FortiGate access** | Admin access to the FortiGate GUI or CLI to create an API user |
| **FortiGate firmware** | FortiOS 6.4 or later (tested on 7.4.x) |
| **Palo Alto access** | Admin access to Panorama or a Palo Alto firewall with API enabled |
| **PAN-OS version** | PAN-OS 10.0 or later recommended |
| **Workstation** | Windows, macOS, or Linux with network access to both firewalls |
| **Python** | Version 3.7 or later |
| **Terraform** | Version 1.0 or later |

### Skill Level

You do **not** need prior experience with:
- Terraform (see [Appendix A](#appendix-a-terraform-concepts-for-firewall-engineers) for a crash course)
- REST APIs (the script handles all API calls)
- Python programming (you just run the script)

---

## 4. Phase 1: Prepare Your FortiGate

### 4.1 Create a REST API Administrator

The script reads your FortiGate configuration through its REST API. You need an API key.

1. Log into your FortiGate web interface (`https://<fortigate-ip>`)
2. Navigate to **System > Administrators**
3. Click **Create New > REST API Admin**
4. Fill in the fields:

   | Field | Value |
   |-------|-------|
   | Username | `migration_api` |
   | Administrator Profile | `super_admin_readonly` (or `super_admin` if readonly is unavailable) |
   | Trusted Hosts | The IP address of your workstation (e.g., `10.0.1.50/32`) |

5. Click **OK**
6. **Copy the API key immediately** - it is only shown once

> **Security note:** The API key grants read access to your entire firewall configuration. Store it securely and delete the API admin account after migration is complete.

### 4.2 Test API Connectivity

Open a terminal on your workstation and run:

```bash
curl -k -H "Authorization: Bearer YOUR_API_KEY" \
  "https://YOUR_FORTIGATE_IP/api/v2/cmdb/system/global"
```

You should see JSON output containing your FortiGate system settings. If you see an authentication error, verify:
- The API key is correct
- Your workstation IP is in the trusted hosts list
- You can reach the FortiGate management interface from your workstation

### 4.3 Identify Your VDOM

If your FortiGate uses VDOMs (Virtual Domains), identify which VDOM you want to migrate:

```bash
curl -k -H "Authorization: Bearer YOUR_API_KEY" \
  "https://YOUR_FORTIGATE_IP/api/v2/cmdb/system/vdom"
```

The default VDOM is `root`. If you use multiple VDOMs, you will run the migration script once per VDOM.

### 4.4 Take a Configuration Backup

Before starting, back up your FortiGate configuration:

1. Go to **System > Configuration > Backup**
2. Select **Full Configuration**
3. Download and store the backup file safely

This backup is your safety net - the migration script only **reads** from the FortiGate and does not modify it, but having a backup is always good practice.

---

## 5. Phase 2: Prepare Your Workstation

### 5.1 Install Python

**Windows:**
1. Download Python from https://www.python.org/downloads/
2. During installation, **check "Add Python to PATH"**
3. Open Command Prompt and verify: `python --version`

**macOS:**
```bash
brew install python3
# Or download from https://www.python.org/downloads/
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip

# RHEL/CentOS
sudo yum install python3 python3-pip
```

### 5.2 Install Python Dependencies

```bash
pip3 install requests
```

That is the only Python dependency required.

### 5.3 Install Terraform

**Windows:**
1. Download from https://developer.hashicorp.com/terraform/install
2. Extract the `.zip` file
3. Move `terraform.exe` to a folder in your PATH (e.g., `C:\Windows\System32`)
4. Verify: `terraform --version`

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Linux:**
```bash
# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

Verify the installation:
```bash
terraform --version
```

### 5.4 Download the Migration Toolkit

```bash
git clone https://github.com/gswsystems/fortigate-palo-migration.git
cd fortigate-palo-migration
```

Or download and extract the ZIP from the repository.

---

## 6. Phase 3: Run the Migration Script

### 6.1 Choose Your Script

| Scenario | Script | Command |
|----------|--------|---------|
| Quick migration, core features only | `fortigate_palo_converter.py` | See Option A |
| Full migration with report and enhanced features | `fortigate_palo_enhanced_main.py` | See Option B (recommended) |

### Option A: Basic Migration

```bash
python3 fortigate_palo_converter.py \
  --host https://192.168.1.1 \
  --api-key YOUR_API_KEY \
  --vdom root \
  --no-verify-ssl \
  --output palo_alto.tf
```

### Option B: Enhanced Migration (Recommended)

```bash
python3 fortigate_palo_enhanced_main.py \
  --host https://192.168.1.1 \
  --api-key YOUR_API_KEY \
  --vdom root \
  --no-verify-ssl \
  --enhanced \
  --report migration_report.md \
  --output palo_alto.tf \
  --save-json debug_data.json
```

### Understanding the Command-Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--host` | Yes | The URL of your FortiGate (include `https://`) |
| `--api-key` | Yes* | Your FortiGate REST API key |
| `--username` / `--password` | Yes* | Alternative to `--api-key` - use admin credentials |
| `--vdom` | No | VDOM to export (default: `root`) |
| `--no-verify-ssl` | No | Skip SSL certificate checks (common for self-signed certs) |
| `-o` / `--output` | No | Output Terraform filename (default: `palo_alto.tf`) |
| `--device-group` | No | Palo Alto device group name (default: `shared`). Use when targeting Panorama |
| `--vsys` | No | Palo Alto vsys (default: `vsys1`) |
| `--template` | No | Palo Alto template name. **Required for zones and static routes** |
| `--enhanced` | No | Enable enhanced features (IPv6, VPN, routing analysis) |
| `--report` | No | Generate a migration report in Markdown format |
| `--save-json` | No | Save raw FortiGate API responses for debugging |

*Provide either `--api-key` or both `--username` and `--password`.

### Using Environment Variables (Optional)

Instead of passing credentials on the command line, you can set environment variables:

```bash
# Linux / macOS
export FORTIGATE_HOST="https://192.168.1.1"
export FORTIGATE_API_KEY="your-api-key-here"
export FORTIGATE_VDOM="root"

# Then run without those flags
python3 fortigate_palo_converter.py --no-verify-ssl --output palo_alto.tf
```

```powershell
# Windows PowerShell
$env:FORTIGATE_HOST = "https://192.168.1.1"
$env:FORTIGATE_API_KEY = "your-api-key-here"
$env:FORTIGATE_VDOM = "root"

python fortigate_palo_converter.py --no-verify-ssl --output palo_alto.tf
```

### When to Use `--template`

The `--template` flag controls whether zones and static routes are included in the output:

- **Without `--template`:** The script generates address objects, services, security policies, and NAT rules. Zones and routes are skipped. Use this when you plan to configure zones and routing manually or when deploying to a Panorama device group where templates are managed separately.

- **With `--template "My-Template"`:** The script also generates zone and static route resources. Use this when you want a more complete migration and your Palo Alto device uses a named template (common in Panorama-managed deployments).

### When to Use `--device-group`

- **Standalone Palo Alto firewall:** Use the default (`shared`) or omit the flag entirely
- **Panorama-managed deployment:** Set this to your device group name (e.g., `--device-group "Branch-Offices"`)

---

## 7. Phase 4: Understand the Output

After running the script, you will have up to three output files:

### 7.1 The Terraform File (`palo_alto.tf`)

This is the main output. It contains Terraform "resources" - each one represents a configuration object that will be created on the Palo Alto. The file is organized in sections:

```
palo_alto.tf
  |
  |-- Provider configuration (tells Terraform how to connect to Palo Alto)
  |-- Address objects (IP addresses, subnets, FQDNs, ranges)
  |-- Address groups (groups of address objects)
  |-- Service objects (TCP/UDP port definitions)
  |-- Service groups (groups of service objects)
  |-- Zones (if --template was specified)
  |-- NAT pools (IP pools converted to address objects)
  |-- Security policies (allow/deny rules)
  |-- NAT policies (source NAT and destination NAT / VIPs)
  |-- Static routes (if --template was specified)
```

**Example: An address object in the Terraform file:**

```hcl
resource "panos_address" "web_server_1" {
  name         = "web_server_1"
  value        = "10.0.1.50/32"
  type         = "ip-netmask"
  description  = "Production web server"
  device_group = "shared"
}
```

This tells Terraform: "Create an address object on the Palo Alto called `web_server_1` with the IP `10.0.1.50/32`."

**Look for lines starting with `# MANUAL MIGRATION REQUIRED`** - these mark items that could not be automatically converted (such as ICMP services or geography-based objects) and need manual attention.

### 7.2 The Migration Report (`migration_report.md`)

Only generated when using the enhanced script with `--report`. This Markdown file contains:

- **Executive Summary** - Counts of all objects discovered and estimated migration time
- **Automated Components** - What the Terraform file will handle
- **Manual Task List** - Prioritised list of items requiring manual configuration, with step-by-step instructions for each
- **VPN Worksheet** - Complete parameter tables for each IPsec tunnel, with example Palo Alto configuration
- **Routing Worksheet** - OSPF/BGP parameters and Palo Alto configuration steps
- **Security Profile Guide** - How to recreate your FortiGate security profiles on Palo Alto
- **Validation Checklist** - Tests to run after migration
- **Rollback Plan** - How to undo the migration if needed

**Open this file in any Markdown viewer** (VS Code, a web browser with a Markdown extension, or GitHub) to read it comfortably.

### 7.3 The Debug JSON (`debug_data.json`)

Only generated when using `--save-json`. Contains the raw API responses from your FortiGate. Useful for troubleshooting if objects are missing or incorrectly converted. You do not need this file for the migration itself.

---

## 8. Phase 5: Prepare Palo Alto for Terraform

### 8.1 Enable API Access on Palo Alto

Terraform communicates with the Palo Alto via its XML/REST API. Ensure API access is enabled:

1. Log into Panorama or the Palo Alto firewall web interface
2. Navigate to **Device > Setup > Management > Management Interface Settings**
3. Ensure **HTTPS** and **API** are enabled
4. Note the management IP address

### 8.2 Create an Admin Account for Terraform

It is good practice to use a dedicated account:

1. Navigate to **Device > Administrators**
2. Create a new administrator:

   | Field | Value |
   |-------|-------|
   | Name | `terraform_admin` |
   | Authentication Profile | Local |
   | Password | (use a strong password) |
   | Admin Role | Superuser (or a custom role with configuration read/write) |

### 8.3 Set Up the Terraform Working Directory

Create a dedicated directory for your migration:

```bash
mkdir palo-migration
cd palo-migration
```

Copy the generated Terraform file into this directory:

```bash
cp /path/to/palo_alto.tf .
```

### 8.4 Configure Terraform Authentication

The generated `palo_alto.tf` file includes a provider block but leaves credentials blank for security. You need to tell Terraform how to connect to your Palo Alto.

**Method 1: Environment variables (recommended)**

```bash
# Linux / macOS
export PANOS_HOSTNAME="panorama.company.com"
export PANOS_USERNAME="terraform_admin"
export PANOS_PASSWORD="your-secure-password"
```

```powershell
# Windows PowerShell
$env:PANOS_HOSTNAME = "panorama.company.com"
$env:PANOS_USERNAME = "terraform_admin"
$env:PANOS_PASSWORD = "your-secure-password"
```

**Method 2: Variables file**

Create a file called `terraform.tfvars` in the same directory:

```hcl
panos_hostname = "panorama.company.com"
panos_username = "terraform_admin"
panos_password = "your-secure-password"
```

Then update the provider block in `palo_alto.tf` to use variables:

```hcl
provider "panos" {
  hostname = var.panos_hostname
  username = var.panos_username
  password = var.panos_password
}

variable "panos_hostname" { type = string }
variable "panos_username" { type = string; sensitive = true }
variable "panos_password" { type = string; sensitive = true }
```

> **Security note:** Add `terraform.tfvars` to your `.gitignore` file if using version control. Never commit passwords to a repository.

**Method 3: API key**

If you prefer to use an API key instead of username/password:

```bash
# Generate an API key
curl -k -X POST "https://panorama.company.com/api/?type=keygen&user=terraform_admin&password=YOUR_PASSWORD"
```

Then set:
```bash
export PANOS_API_KEY="your-api-key-from-above"
export PANOS_HOSTNAME="panorama.company.com"
```

---

## 9. Phase 6: Review the Terraform Plan

This is the most important safety step. Terraform will show you exactly what it plans to create **before** making any changes.

### 9.1 Initialize Terraform

This downloads the Palo Alto provider plugin:

```bash
terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
- Finding paloaltonetworks/panos versions matching "~> 1.13"...
- Installing paloaltonetworks/panos v1.13.x...

Terraform has been successfully initialized!
```

If you see errors about the provider, check your internet connection. Terraform needs to download the provider plugin the first time.

### 9.2 Validate the Configuration

Check for syntax errors:

```bash
terraform validate
```

If validation reports errors, see [Troubleshooting](#15-troubleshooting).

### 9.3 Generate the Plan

```bash
terraform plan -out=migration.plan
```

This connects to your Palo Alto, compares the desired state (your `.tf` file) with the current state (what exists on the device), and shows what will change.

**Review the output carefully.** You will see entries like:

```
  # panos_address.web_server_1 will be created
  + resource "panos_address" "web_server_1" {
      + name         = "web_server_1"
      + value        = "10.0.1.50/32"
      + type         = "ip-netmask"
      + description  = "Production web server"
      + device_group = "shared"
    }
```

The `+` symbol means "will be created." At the end, Terraform shows a summary:

```
Plan: 247 to add, 0 to change, 0 to destroy.
```

### 9.4 What to Look For

**Check the resource count.** The number of Terraform resources should roughly correspond to what the migration script reported:
- Address objects should match the count from the script output
- Security policies should match the number of enabled policies on your FortiGate
- NAT rules should match policies with NAT enabled plus your VIP count

**Check for naming conflicts.** If your Palo Alto already has objects with the same names as the FortiGate objects, Terraform will fail. You will need to either:
- Import the existing objects into Terraform state (advanced)
- Rename the conflicting objects on one side
- Remove duplicates from the `.tf` file

**Check zone mappings.** FortiGate uses interface names as implicit zones. The script maps these to Palo Alto zones with the same names. Review that these zone names make sense for your Palo Alto deployment.

---

## 10. Phase 7: Apply the Configuration

### 10.1 Before You Apply

Checklist:
- [ ] You have reviewed the `terraform plan` output
- [ ] You have a backup of your Palo Alto running configuration
- [ ] You are in a maintenance window (or applying to a non-production device first)
- [ ] You have console access to the Palo Alto in case the API becomes unreachable

### 10.2 Back Up the Palo Alto Configuration

Before making changes:

**Via GUI:**
1. Go to **Device > Setup > Operations**
2. Click **Export named configuration snapshot**
3. Select **running-config.xml**
4. Save the file

**Via CLI:**
```
scp export configuration running-config.xml from running-config.xml to admin@your-workstation:/backup/
```

### 10.3 Apply the Plan

```bash
terraform apply migration.plan
```

Terraform will create each resource in order, respecting dependencies (e.g., address objects are created before address groups that reference them).

You will see output like:
```
panos_address.web_server_1: Creating...
panos_address.web_server_1: Creation complete after 2s
panos_address.db_server_1: Creating...
panos_address.db_server_1: Creation complete after 1s
...
Apply complete! Resources: 247 added, 0 changed, 0 destroyed.
```

If a resource fails, Terraform will stop and report the error. Resources that were already created remain in place. Fix the error and run `terraform apply` again - it will skip already-created resources and continue from where it left off.

### 10.4 Commit on Palo Alto

Terraform creates the configuration as a **candidate configuration** on the Palo Alto. You need to commit it to make it active.

> **Important:** On Panorama-managed deployments, you also need to push the configuration to your managed firewalls.

**Via GUI:**
1. Log into Panorama or the Palo Alto firewall
2. Click **Commit** in the top right
3. Select **Commit to Panorama** (or **Commit** for standalone)
4. Review the changes and click **Commit**
5. If using Panorama: click **Commit > Push to Devices** to push to managed firewalls

**Via CLI:**
```
commit
```

### 10.5 Save the Terraform State

After applying, Terraform creates a file called `terraform.tfstate` in your working directory. **This file is important** - it maps Terraform resources to real objects on the Palo Alto. Back it up:

```bash
cp terraform.tfstate terraform.tfstate.backup
```

You will need this file if you want to update or remove the migrated configuration later.

---

## 11. Phase 8: Manual Configuration Tasks

The automated migration handles the bulk of the work, but some items require manual attention. If you generated a migration report (`--report`), open it now and follow the task list.

### 11.1 Security Profiles

FortiGate security profiles (antivirus, IPS, web filtering) do not have a direct 1:1 mapping to Palo Alto. You need to create equivalent profiles manually.

**Antivirus:**
1. Go to **Objects > Security Profiles > Antivirus**
2. Click **Add**
3. Configure decoder settings for each protocol (HTTP, SMTP, IMAP, POP3, FTP, SMB)
4. Enable WildFire analysis for unknown files
5. Apply the profile to your security policies

**Vulnerability Protection (replaces FortiGate IPS):**
1. Go to **Objects > Security Profiles > Vulnerability Protection**
2. Click **Add**
3. Select threat severity levels to block
4. Consider starting with the `strict` built-in profile and customising from there

**URL Filtering (replaces FortiGate Web Filter):**
1. Go to **Objects > Security Profiles > URL Filtering**
2. Click **Add**
3. Configure URL category actions (allow, alert, block)
4. Add custom URL lists if needed

> **Tip:** Palo Alto provides built-in "best practice" profiles. Start with these and customise rather than building from scratch.

### 11.2 VPN Tunnels

If you have IPsec VPN tunnels, the migration report includes a worksheet for each tunnel with all the parameters you need. For each tunnel:

1. **Create an IKE Crypto Profile:** Network > Network Profiles > IKE Crypto
   - Match the encryption, authentication, and DH group from your FortiGate Phase 1 settings

2. **Create an IPsec Crypto Profile:** Network > Network Profiles > IPsec Crypto
   - Match the encryption, authentication, and DH group from your FortiGate Phase 2 settings

3. **Create an IKE Gateway:** Network > IKE Gateways
   - Set the peer IP address, interface, IKE version, and pre-shared key
   - Select the IKE Crypto Profile you created above

4. **Create a Tunnel Interface:** Network > Interfaces > Tunnel
   - Assign it to a security zone (create a "vpn" zone if needed)
   - Assign it to a virtual router

5. **Create an IPsec Tunnel:** Network > IPsec Tunnels
   - Link the IKE Gateway and IPsec Crypto Profile
   - Configure proxy IDs if needed (must match FortiGate Phase 2 selectors)

6. **Create security policies** to allow traffic through the tunnel

### 11.3 Dynamic Routing (OSPF / BGP)

If your FortiGate uses OSPF or BGP, configure them on the Palo Alto:

**OSPF:**
1. Go to **Network > Virtual Routers > (select your VR)**
2. Click the **OSPF** tab and enable it
3. Set the Router ID (use the same as your FortiGate if possible)
4. Add areas and assign interfaces
5. Configure redistribution rules if needed

**BGP:**
1. Go to **Network > Virtual Routers > (select your VR)**
2. Click the **BGP** tab and enable it
3. Set the AS number and Router ID
4. Configure peer groups and add neighbours
5. Set import/export route filters

### 11.4 Application-ID Migration

FortiGate policies use port-based service objects (e.g., "allow TCP/443"). Palo Alto's strength is Application-ID, which identifies traffic by application regardless of port.

After the initial migration, consider replacing port-based rules with App-ID rules:

**Before (port-based, as migrated):**
```
Services: service-tcp-443
Applications: any
```

**After (App-ID optimized):**
```
Services: application-default
Applications: ssl, web-browsing
```

This is not urgent for day-one cutover but should be planned as a post-migration optimization.

---

## 12. Phase 9: Validate the Migration

### 12.1 Configuration Verification

On the Palo Alto CLI or GUI, verify that objects were created correctly:

**Check address objects:**
```
show config merged | match "address "
```

**Check security policies:**
```
show config merged | match "security rules"
```

**Count objects:**

| Object Type | Palo Alto GUI Location |
|-------------|----------------------|
| Addresses | Objects > Addresses |
| Address Groups | Objects > Address Groups |
| Services | Objects > Services |
| Service Groups | Objects > Service Groups |
| Security Policies | Policies > Security |
| NAT Policies | Policies > NAT |
| Static Routes | Network > Virtual Routers > (VR) > Static Routes |
| Zones | Network > Zones |

Compare counts with the migration script output to ensure nothing was missed.

### 12.2 Policy Match Testing

Test that policies will match traffic correctly. From the Palo Alto CLI:

**Test a security policy match:**
```
test security-policy-match source 192.168.1.10 destination 8.8.8.8 protocol 6 destination-port 443
```

This should return the policy that would match traffic from `192.168.1.10` going to `8.8.8.8` on TCP/443.

**Test a NAT policy match:**
```
test nat-policy-match source 192.168.1.10 destination 8.8.8.8 protocol 6 destination-port 443
```

Run these tests for your most critical traffic flows:
- Internal users to internet
- Incoming connections to public-facing servers (VIPs)
- Site-to-site VPN traffic
- Inter-VLAN traffic

### 12.3 Routing Verification

```
show routing route
show routing summary
show routing protocol ospf summary    # if using OSPF
show routing protocol bgp summary     # if using BGP
```

### 12.4 VPN Verification

```
show vpn ike-sa
show vpn ipsec-sa
```

---

## 13. Phase 10: Cutover

### 13.1 Pre-Cutover Checklist

- [ ] All automated objects verified on Palo Alto
- [ ] Manual tasks completed (VPN, routing, security profiles)
- [ ] Policy match tests passing for critical flows
- [ ] VPN tunnels established (if applicable)
- [ ] Routing neighbours up (if applicable)
- [ ] Maintenance window communicated to stakeholders
- [ ] Rollback plan reviewed with team
- [ ] Console access available to both FortiGate and Palo Alto
- [ ] Monitoring dashboards open (traffic logs, system resources)

### 13.2 Cutover Steps

1. **Final sync:** Re-run the migration script to catch any last-minute FortiGate changes. Run `terraform plan` to see if anything changed. Apply if needed.

2. **Switch traffic:** The exact method depends on your network design:
   - **Layer 3 cutover:** Change upstream router next-hop from FortiGate to Palo Alto
   - **VRRP/HSRP:** Adjust priority so Palo Alto becomes active
   - **Physical swap:** Move cables from FortiGate to Palo Alto interfaces

3. **Monitor:** Watch the Palo Alto traffic logs closely for the first hour:
   - **Monitor > Traffic** in the GUI
   - Look for denied traffic that should be allowed (missing policy)
   - Look for traffic hitting the wrong policy (rule ordering)

4. **Keep the FortiGate available:** Do not decommission the FortiGate immediately. Keep it powered on and cabled for at least 48-72 hours as a quick rollback option.

### 13.3 Post-Cutover Monitoring

For the first 48-72 hours, watch for:

| Issue | Where to Look | Action |
|-------|--------------|--------|
| Blocked traffic | Monitor > Traffic (filter: action = deny) | Add or fix security policy |
| NAT failures | Monitor > Traffic (filter: natdport != 0) | Check NAT rule ordering |
| VPN drops | Monitor > System (filter: subtype = vpn) | Check IKE/IPsec settings |
| Route issues | `show routing route` | Verify static routes and routing protocols |
| Performance | Dashboard > Widgets > System Resources | Check session count, CPU, memory |

---

## 14. Rollback Procedures

### Option 1: Terraform Destroy

Remove all Terraform-managed objects from the Palo Alto:

```bash
terraform destroy
```

Type `yes` to confirm. This removes only the objects Terraform created - it does not affect any manually created configuration.

Then commit the empty candidate configuration:
```
commit
```

Switch traffic back to the FortiGate.

### Option 2: Restore Palo Alto Configuration Backup

If Terraform destroy is not possible or you made manual changes you want to undo:

1. Go to **Device > Setup > Operations**
2. Click **Import named configuration snapshot**
3. Select the backup you created in [Phase 7](#102-back-up-the-palo-alto-configuration)
4. Click **Load named configuration snapshot**
5. Select the imported file
6. Click **Commit**

### Option 3: Traffic Reroute

The fastest rollback - simply route traffic back to the FortiGate:

1. Reverse whatever routing change you made during cutover
2. Verify traffic is flowing through the FortiGate
3. Troubleshoot the Palo Alto offline
4. Retry cutover when ready

---

## 15. Troubleshooting

### Script Errors

**`SSL: CERTIFICATE_VERIFY_FAILED`**

Your FortiGate uses a self-signed certificate. Add `--no-verify-ssl`:

```bash
python3 fortigate_palo_converter.py --host https://192.168.1.1 --api-key KEY --no-verify-ssl
```

**`API request failed: 401`**

Authentication failed. Verify:
- Your API key is correct (no extra spaces or line breaks)
- The API admin account has not expired
- Your workstation IP is in the trusted hosts list

**`API request failed: 403`**

Permission denied. The API admin account needs `super_admin` or `super_admin_readonly` profile.

**`API request failed: 404`**

The endpoint does not exist on your FortiOS version. The script handles this gracefully for most endpoints, but if you see this repeatedly, verify your FortiOS version is 6.4 or later.

**`Connection refused` or `Connection timed out`**

- Verify the FortiGate management IP and port
- Check that HTTPS management is enabled
- Check for firewalls between your workstation and the FortiGate

### Terraform Errors

**`Error: Provider produced inconsistent result`**

The object already exists on the Palo Alto with a different configuration. Options:
- Delete the conflicting object from the Palo Alto and re-run `terraform apply`
- Remove the resource from the `.tf` file if you want to keep the existing object
- Import the existing object: `terraform import panos_address.web_server_1 shared:web_server_1`

**`Error: Object not found`**

A security policy references an address or service object that does not exist. This usually means:
- The referenced object uses a built-in FortiGate name (like `all`) that was mapped to `any` but not quite correctly
- A group member references an object that was filtered out during conversion

Check the specific error message, find the resource in `palo_alto.tf`, and fix the reference.

**`Error: Invalid value for...`**

A value does not meet Palo Alto's validation rules. Common issues:
- Object names longer than 63 characters
- Special characters in names that Palo Alto does not allow
- Empty values where a value is required

Edit the `.tf` file to fix the value and re-run `terraform apply`.

**`terraform init` fails**

- Check your internet connection (Terraform needs to download the panos provider)
- If behind a proxy, set `HTTP_PROXY` and `HTTPS_PROXY` environment variables
- Try: `terraform init -upgrade` to refresh provider versions

### Migration Issues

**Objects are missing from the output**

Run the script with `--save-json debug.json` and examine the JSON file. Check whether:
- The objects exist in the VDOM you specified
- The objects are of a type the script supports (see [What Gets Migrated](#2-what-gets-migrated))

**Policy ordering seems wrong**

The script preserves the order of policies as they appear on the FortiGate. Each policy is placed at the `bottom` position. If you need different ordering, edit the `position_keyword` in the `.tf` file or reorder the resources.

**NAT rules are not working**

Palo Alto NAT evaluation order differs from FortiGate:
1. Palo Alto evaluates destination NAT first, then security policy, then source NAT
2. FortiGate evaluates the policy first

This means you may need to adjust your security policies to reference the **pre-NAT** destination for destination NAT (VIP) scenarios.

---

## Appendix A: Terraform Concepts for Firewall Engineers

If you have never used Terraform before, here is what you need to know for this migration:

### What is Terraform?

Terraform is an infrastructure automation tool. You describe what you want (in `.tf` files), and Terraform makes it happen. Think of it as a "configuration script" for your Palo Alto.

### Key Concepts

| Terraform Term | Firewall Analogy |
|----------------|-----------------|
| **Provider** | The connection method. Like SSH or API credentials for your device. |
| **Resource** | A single configuration object. One address object = one resource. |
| **State** | Terraform's record of what it has created. Like a changelog. |
| **Plan** | A preview of what Terraform will do. Like "show candidate diff." |
| **Apply** | Execute the plan. Like clicking "Commit." |
| **Destroy** | Remove everything Terraform created. Like "Revert to last saved config." |

### The Terraform Workflow

```
terraform init      # Download the Palo Alto plugin (once)
terraform validate  # Check for syntax errors
terraform plan      # Preview changes (safe - read-only)
terraform apply     # Make the changes (creates objects on Palo Alto)
terraform destroy   # Remove all created objects (rollback)
```

### Reading a .tf File

```hcl
resource "panos_address" "web_server" {
  name         = "web_server"        # Object name on Palo Alto
  value        = "10.0.1.50/32"      # The IP address
  type         = "ip-netmask"        # Address type
  description  = "Web server"        # Description field
  device_group = "shared"            # Where to create it
}
```

- `resource` = "I want to create this thing"
- `"panos_address"` = the type of object (address, service, policy, etc.)
- `"web_server"` = Terraform's internal name for tracking (not visible on the Palo Alto)
- Everything inside `{ }` = the object's properties

### What is `terraform.tfstate`?

This file records what Terraform has created. It allows Terraform to:
- Know what already exists (so it does not create duplicates)
- Detect changes (so it can update objects)
- Remove objects cleanly (on `terraform destroy`)

**Never delete this file** while you have active Terraform-managed objects on your Palo Alto. If you lose it, Terraform will not know about the existing objects and will try to create duplicates.

---

## Appendix B: FortiGate to Palo Alto Terminology Map

| FortiGate | Palo Alto | Notes |
|-----------|-----------|-------|
| Address object | Address object | Direct equivalent |
| Address group | Address group | Direct equivalent |
| Service (custom) | Service object | Direct equivalent |
| Service group | Service group | Direct equivalent |
| Firewall policy | Security rule | Palo Alto separates security and NAT into different rulebases |
| Policy with NAT enabled | Security rule + NAT rule | Two separate objects on Palo Alto |
| Virtual IP (VIP) | NAT rule (DNAT) | Destination NAT is a separate rule on Palo Alto |
| IP Pool | Address object (for NAT) | Palo Alto references address objects in NAT rules |
| Interface / Zone | Zone | Palo Alto always uses zones, never bare interfaces in policies |
| VDOM | Virtual system (vsys) | Similar concept, different implementation |
| Static route | Static route | Direct equivalent |
| FortiGuard | Threat Prevention / WildFire | Different subscription model |
| UTM profile | Security profile group | Palo Alto uses individual profiles attached to rules |
| `action: accept` | `action: allow` | Different keyword |
| `srcaddr: all` | `source_addresses: any` | Different keyword |
| `service: ALL` | `services: application-default` or `any` | Palo Alto prefers App-ID |

---

## Appendix C: What Cannot Be Automated

These items require a fundamentally different approach on Palo Alto and cannot be converted by any automated tool:

| Feature | Why | What To Do |
|---------|-----|------------|
| **SSL inspection profiles** | Different architecture (Palo Alto uses decryption policies + certificate management) | Create decryption policies manually; deploy CA certificates to endpoints |
| **Application control** | FortiGate uses signature-based app detection; Palo Alto uses App-ID natively | Replace port-based rules with App-ID rules post-migration |
| **SD-WAN** | Completely different implementation | Evaluate Prisma SD-WAN or configure policy-based forwarding |
| **HA (High Availability)** | Platform-specific (heartbeat interfaces, failover timers) | Configure HA natively on Palo Alto |
| **Security Fabric** | Fortinet proprietary; Panorama is the Palo Alto equivalent | Deploy Panorama for centralised management |
| **FortiTokens / FortiAuthenticator** | Proprietary MFA; Palo Alto integrates with third-party MFA | Deploy GlobalProtect with SAML or RADIUS-based MFA |
| **Traffic shaping / QoS** | Different model (FortiGate per-policy; Palo Alto per-interface QoS) | Configure QoS profiles on Palo Alto interfaces |
| **Custom IPS signatures** | Different signature format | Recreate as custom vulnerability signatures or use Palo Alto threat feeds |

---

*Guide generated for the FortiGate to Palo Alto Migration Toolkit. For tool issues, see the project repository.*
