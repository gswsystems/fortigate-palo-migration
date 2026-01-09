# FortiGate to Palo Alto Networks Migration Toolkit

![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-green.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)

Comprehensive Python toolkit for migrating firewall configurations from FortiGate to Palo Alto Networks using Terraform with the latest panos provider.

**Copyright © 2025 GSW Systems. All rights reserved.**  
**License:** GNU Affero General Public License v3.0 (AGPL-3.0)  
**Contact:** sales@gswsystems.com  

---

## Features

### Maximum Coverage

#### Address Objects
- ✓ IP/Netmask addresses
- ✓ IP Range addresses
- ✓ FQDN addresses
- ✓ Wildcard addresses (IP-wildcard)
- ✓ Geography-based addresses
- ✓ Address groups (static and dynamic)
- ✓ Nested address groups
- ✓ Interface-specific addresses

#### Service Objects
- ✓ TCP services (single and ranges)
- ✓ UDP services (single and ranges)
- ✓ SCTP services
- ✓ IP protocol numbers
- ✓ Service groups
- ✓ Nested service groups
- ⚠ ICMP/ICMPv6 (manual migration notes)

#### Firewall Policies
- ✓ Security rules (allow/deny)
- ✓ Source zones and interfaces
- ✓ Destination zones and interfaces
- ✓ Source addresses (any, all, specific)
- ✓ Destination addresses (any, all, specific)
- ✓ Service matching
- ✓ Action mapping (accept → allow, deny → deny)
- ✓ Logging configuration
- ✓ Comments and descriptions
- ✓ Policy ordering (top, bottom)
- ⚠ Security profiles (notes for manual config)

#### NAT Configuration
- ✓ Source NAT (dynamic IP and port)
- ✓ NAT pools (IP pools)
- ✓ Interface-based source NAT
- ✓ Virtual IPs (VIP) - destination NAT
- ✓ Port forwarding / PAT
- ✓ Static 1:1 NAT
- ✓ VIP groups

#### Network Configuration
- ✓ Static routes
- ✓ Virtual routers
- ✓ Zones (layer3)
- ✓ Interface mapping
- ✓ VLAN interfaces

## Requirements

```bash
pip install -r requirements.txt
```

Requirements:
- Python 3.7+
- requests
- urllib3

## Installation

```bash
# Clone or download the script
chmod +x fortigate_palo_converter.py

# Install dependencies
pip install requests urllib3
```

## FortiGate API Setup

### Option 1: API Key (Recommended)

1. Login to FortiGate web interface
2. Go to **System > Administrators**
3. Create a new REST API Admin:
   - **Username**: api_user
   - **Administrator Profile**: super_admin (or custom with read permissions)
   - **REST API Admin**: Enable
   - **Trusted Hosts**: Add your source IP
4. Generate API key and save it securely

### Option 2: Username/Password

Use existing admin credentials (less secure, session-based).

## Usage

### Basic Usage with API Key

```bash
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --api-key YOUR_API_KEY_HERE
```

### With Username/Password

```bash
./fortigate_palo_converter.py \
  --host 192.168.1.1 \
  --username admin \
  --password password123
```

### Specify VDOM

```bash
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --api-key YOUR_API_KEY \
  --vdom production
```

### Custom Output and Device Group

```bash
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --api-key YOUR_API_KEY \
  --device-group "Production-DG" \
  --vsys vsys2 \
  --output prod_firewall.tf
```

### With Template for Network Configuration

```bash
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --api-key YOUR_API_KEY \
  --template "Production-Template" \
  --output complete_config.tf
```

### Save Debug Information

```bash
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --api-key YOUR_API_KEY \
  --save-json debug_output.json
```

### Using Environment Variables

```bash
export FORTIGATE_HOST="firewall.example.com"
export FORTIGATE_API_KEY="your-api-key"
export FORTIGATE_VDOM="production"

./fortigate_palo_converter.py --output migration.tf
```

## Configuration Options

| Parameter | Environment Variable | Description | Default |
|-----------|---------------------|-------------|---------|
| `--host` | `FORTIGATE_HOST` | FortiGate hostname/IP | (required) |
| `--api-key` | `FORTIGATE_API_KEY` | API authentication key | - |
| `--username` | `FORTIGATE_USERNAME` | Admin username | - |
| `--password` | `FORTIGATE_PASSWORD` | Admin password | - |
| `--vdom` | `FORTIGATE_VDOM` | Virtual domain | root |
| `--device-group` | - | Palo Alto device group | shared |
| `--vsys` | - | Palo Alto virtual system | vsys1 |
| `--template` | - | Palo Alto template name | - |
| `-o, --output` | - | Output Terraform file | palo_alto.tf |
| `--no-verify-ssl` | - | Disable SSL verification | false |
| `--save-json` | - | Save raw API data to JSON | - |

## Output Structure

The script generates a complete Terraform configuration with:

```
palo_alto.tf
├── Provider Configuration
├── Address Objects
├── Address Groups
├── Service Objects
├── Service Groups
├── Zones (if template specified)
├── NAT Pools
├── Security Policies
│   ├── Allow Rules
│   └── Deny Rules
├── NAT Policies
│   ├── Source NAT
│   └── Destination NAT (VIPs)
└── Static Routes (if template specified)
```

## Post-Migration Steps

### 1. Review Generated Configuration

```bash
# Open and review the Terraform file
vim palo_alto.tf

# Check for manual migration notes
grep "MANUAL MIGRATION" palo_alto.tf
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Configure Palo Alto Provider

Create `terraform.tfvars`:

```hcl
# Option 1: Username/Password
panos_hostname = "panorama.example.com"
panos_username = "admin"
panos_password = "password"

# Option 2: API Key
panos_hostname = "panorama.example.com"
panos_api_key  = "your-api-key"
```

Or use environment variables:

```bash
export PANOS_HOSTNAME="panorama.example.com"
export PANOS_USERNAME="admin"
export PANOS_PASSWORD="password"
```

### 4. Plan and Apply

```bash
# Review changes
terraform plan

# Apply configuration
terraform apply
```

### 5. Manual Review Required For

- **Zone Assignments**: Verify interface-to-zone mappings
- **ICMP Services**: Create application or custom application objects
- **Security Profiles**: 
  - Antivirus profiles
  - IPS sensors
  - URL filtering
  - File blocking
  - Data filtering
- **Application-Based Policies**: Convert to App-ID
- **SSL/SSH Inspection**: Configure decryption policies
- **QoS Settings**: Policy-based forwarding
- **User/Group Objects**: Identity-based policies
- **VPN Configuration**: Site-to-site and remote access VPNs

## Examples

### Example 1: Basic Migration

```bash
# Export from FortiGate via API
./fortigate_palo_converter.py \
  --host 10.1.1.1 \
  --api-key "abc123xyz" \
  --output basic_migration.tf

# Review and apply
terraform init
terraform plan
terraform apply
```

### Example 2: Multi-VDOM with Custom Device Groups

```bash
# Migrate production VDOM
./fortigate_palo_converter.py \
  --host firewall.corp.local \
  --api-key "prod-key" \
  --vdom production \
  --device-group "Production-DG" \
  --template "Prod-Template" \
  --output prod_fw.tf

# Migrate development VDOM
./fortigate_palo_converter.py \
  --host firewall.corp.local \
  --api-key "dev-key" \
  --vdom development \
  --device-group "Dev-DG" \
  --template "Dev-Template" \
  --output dev_fw.tf
```

### Example 3: Debug and Troubleshoot

```bash
# Save all API responses for analysis
./fortigate_palo_converter.py \
  --host firewall.example.com \
  --username admin \
  --password pass123 \
  --save-json raw_config.json \
  --output debug_migration.tf

# Analyze the JSON
jq '.policies[] | select(.action == "accept")' raw_config.json
```

## Mapping Reference

### Action Mapping

| FortiGate | Palo Alto |
|-----------|-----------|
| accept | allow |
| deny | deny |
| reject | deny |

### Address Type Mapping

| FortiGate | Palo Alto |
|-----------|-----------|
| ipmask | ip-netmask |
| iprange | ip-range |
| fqdn | fqdn |
| wildcard | ip-wildcard |
| geography | EDL or manual |

### Protocol Mapping

| FortiGate | Palo Alto |
|-----------|-----------|
| TCP | tcp |
| UDP | udp |
| ICMP | (manual - application) |
| IP | protocol number |

### NAT Type Mapping

| FortiGate | Palo Alto |
|-----------|-----------|
| IP Pool (overload) | Dynamic IP and Port |
| IP Pool (one-to-one) | Static IP |
| VIP | Destination NAT |
| Port Forwarding | Dest NAT with port |

## Troubleshooting

### SSL Certificate Errors

```bash
# Disable SSL verification (not recommended for production)
./fortigate_palo_converter.py \
  --host firewall.local \
  --api-key KEY \
  --no-verify-ssl
```

### Authentication Failures

```bash
# Verify API key has correct permissions
curl -k -H "Authorization: Bearer YOUR_API_KEY" \
  "https://firewall.local/api/v2/cmdb/firewall/policy?vdom=root"

# Check VDOM access
curl -k -H "Authorization: Bearer YOUR_API_KEY" \
  "https://firewall.local/api/v2/cmdb/system/vdom"
```

### Missing Objects

```bash
# Save debug JSON and check
./fortigate_palo_converter.py --save-json debug.json ...

# Verify objects exist in FortiGate
jq '.addresses[] | .name' debug.json
```

## Known Limitations

1. **ICMP Services**: Require manual migration to application objects
2. **Application Layer**: FortiGate application control needs App-ID mapping
3. **Security Profiles**: Profiles are noted but not converted
4. **VPN Tunnels**: Not included in conversion
5. **Dynamic Routing**: OSPF, BGP configurations not converted
6. **High Availability**: HA pairs need manual configuration
7. **User Objects**: Identity-based rules need Palo Alto User-ID setup
8. **SD-WAN**: Policy-based routing needs manual configuration

## API Endpoints Used

The script queries the following FortiGate API endpoints:

- `/api/v2/cmdb/firewall/address` - Address objects
- `/api/v2/cmdb/firewall/addrgrp` - Address groups
- `/api/v2/cmdb/firewall.service/custom` - Service objects
- `/api/v2/cmdb/firewall.service/group` - Service groups
- `/api/v2/cmdb/firewall/policy` - IPv4 policies
- `/api/v2/cmdb/firewall/policy6` - IPv6 policies
- `/api/v2/cmdb/firewall/ippool` - NAT pools
- `/api/v2/cmdb/firewall/vip` - Virtual IPs
- `/api/v2/cmdb/firewall/vipgrp` - VIP groups
- `/api/v2/cmdb/router/static` - Static routes
- `/api/v2/cmdb/system/interface` - Interfaces
- `/api/v2/cmdb/system/zone` - Zones

## Security Considerations

1. **API Keys**: Store securely, never commit to version control
2. **Credentials**: Use environment variables or secure vaults
3. **SSL Verification**: Always verify SSL in production
4. **API Permissions**: Use read-only API accounts when possible
5. **Terraform State**: Protect state files (contain sensitive data)
6. **Review Changes**: Always review `terraform plan` before applying

## Contributing

Suggestions for improvements:
- Additional object type support
- IPv6 policy conversion
- Application-ID mapping
- Security profile conversion
- VPN tunnel migration

## License

This script is provided as-is for firewall migration projects.

## Support

For issues or questions:
1. Check FortiGate API documentation
2. Review Palo Alto Terraform provider docs
3. Validate API connectivity and permissions
4. Use `--save-json` for debugging

## Version History

- v1.0 - Initial release with comprehensive coverage
  - Address objects and groups
  - Service objects and groups
  - Security policies
  - NAT policies and VIPs
  - Static routes and zones
  - FortiGate API integration
