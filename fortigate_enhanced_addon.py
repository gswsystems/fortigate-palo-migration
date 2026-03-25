#!/usr/bin/env python3
"""
FortiGate to Palo Alto Migration - Enhanced Addon Module
Extends base converter with:
- IPv6 support
- VPN migration
- Dynamic routing
- User objects  
- Security profile analysis
- Comprehensive migration report generation

Copyright (C) 2025 GSW Systems
Contact: sales@gswsystems.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class IPv6Address:
    """IPv6 address object"""
    name: str
    type: str  # ip6-mask, ip6-range, fqdn
    ip6: Optional[str] = None
    ip6_range: Optional[tuple] = None
    comment: Optional[str] = None


@dataclass
class IPsecPhase1:
    """IPsec VPN Phase 1 configuration"""
    name: str
    interface: str
    ike_version: str
    peertype: str
    remote_gw: str
    proposal: List[str]
    dhgrp: List[int]
    authmethod: str
    psksecret: Optional[str] = None
    certificate: Optional[str] = None
    dpd: str = "on-demand"
    comment: Optional[str] = None


@dataclass  
class IPsecPhase2:
    """IPsec VPN Phase 2 configuration"""
    name: str
    phase1name: str
    proposal: List[str]
    dhgrp: List[int]
    src_subnet: List[str]
    dst_subnet: List[str]
    pfs: str = "enable"
    comment: Optional[str] = None


@dataclass
class OSPFConfig:
    """OSPF configuration"""
    router_id: str
    areas: List[Dict]
    networks: List[Dict]
    redistribute: List[Dict]


@dataclass
class BGPConfig:
    """BGP configuration"""
    as_number: str
    router_id: str
    neighbors: List[Dict]
    networks: List[Dict]
    redistribute: List[Dict]


@dataclass
class LocalUser:
    """Local user account"""
    name: str
    type: str  # password, radius, ldap, etc
    status: str
    comment: Optional[str] = None


@dataclass
class UserGroup:
    """User group"""
    name: str
    members: List[str]
    comment: Optional[str] = None


@dataclass
class RadiusServer:
    """RADIUS server configuration"""
    name: str
    server: str
    secret: str
    auth_type: str
    timeout: int = 5


@dataclass
class SecurityProfile:
    """Security profile analysis"""
    type: str  # av, ips, webfilter, application
    name: str
    settings: Dict
    policies_using: List[str]


@dataclass
class MigrationTask:
    """Manual migration task"""
    category: str
    priority: str  # critical, high, medium, low
    title: str
    description: str
    fortigate_config: Optional[str] = None
    palo_alto_steps: List[str] = field(default_factory=list)
    reference_docs: List[str] = field(default_factory=list)
    estimated_time: str = "Unknown"


class EnhancedFortiGateAPI:
    """Extended API client with additional endpoints"""
    
    def __init__(self, base_api):
        self.api = base_api

    def _safe_get(self, endpoint: str, default=None):
        """Safely call the API, returning default on error (e.g. removed endpoints in newer FortiOS)"""
        if default is None:
            default = {}
        try:
            return self.api.get(endpoint)
        except Exception:
            return default

    def _safe_get_single(self, endpoint: str) -> dict:
        """Safely get a singleton config object (ospf, bgp, ha, etc.)
        Handles both list and dict results across FortiOS versions."""
        result = self._safe_get(endpoint)
        results = result.get('results', {})
        if isinstance(results, list):
            return results[0] if results else {}
        return results if isinstance(results, dict) else {}

    def get_ipv6_addresses(self) -> List[dict]:
        """Get IPv6 address objects"""
        result = self._safe_get('cmdb/firewall/address6')
        return result.get('results', [])

    def get_ipv6_address_groups(self) -> List[dict]:
        """Get IPv6 address groups"""
        result = self._safe_get('cmdb/firewall/addrgrp6')
        return result.get('results', [])

    def get_ipv6_policies(self) -> List[dict]:
        """Get IPv6 firewall policies"""
        result = self._safe_get('cmdb/firewall/policy6')
        return result.get('results', [])

    def get_ipsec_phase1(self) -> List[dict]:
        """Get IPsec Phase 1 interfaces"""
        result = self._safe_get('cmdb/vpn.ipsec/phase1-interface')
        return result.get('results', [])

    def get_ipsec_phase2(self) -> List[dict]:
        """Get IPsec Phase 2 selectors"""
        result = self._safe_get('cmdb/vpn.ipsec/phase2-interface')
        return result.get('results', [])

    def get_ssl_vpn_settings(self) -> dict:
        """Get SSL VPN settings"""
        return self._safe_get_single('cmdb/vpn.ssl/settings')

    def get_ospf_config(self) -> dict:
        """Get OSPF configuration"""
        return self._safe_get_single('cmdb/router/ospf')

    def get_bgp_config(self) -> dict:
        """Get BGP configuration"""
        return self._safe_get_single('cmdb/router/bgp')

    def get_local_users(self) -> List[dict]:
        """Get local user accounts"""
        result = self._safe_get('cmdb/user/local')
        return result.get('results', [])

    def get_user_groups(self) -> List[dict]:
        """Get user groups"""
        result = self._safe_get('cmdb/user/group')
        return result.get('results', [])

    def get_radius_servers(self) -> List[dict]:
        """Get RADIUS servers"""
        result = self._safe_get('cmdb/user/radius')
        return result.get('results', [])

    def get_ldap_servers(self) -> List[dict]:
        """Get LDAP servers"""
        result = self._safe_get('cmdb/user/ldap')
        return result.get('results', [])

    def get_antivirus_profiles(self) -> List[dict]:
        """Get antivirus profiles"""
        result = self._safe_get('cmdb/antivirus/profile')
        return result.get('results', [])

    def get_ips_sensors(self) -> List[dict]:
        """Get IPS sensors"""
        result = self._safe_get('cmdb/ips/sensor')
        return result.get('results', [])

    def get_webfilter_profiles(self) -> List[dict]:
        """Get web filter profiles"""
        result = self._safe_get('cmdb/webfilter/profile')
        return result.get('results', [])

    def get_application_lists(self) -> List[dict]:
        """Get application control lists"""
        result = self._safe_get('cmdb/application/list')
        return result.get('results', [])

    def get_ssl_ssh_profiles(self) -> List[dict]:
        """Get SSL/SSH inspection profiles"""
        result = self._safe_get('cmdb/firewall/ssl-ssh-profile')
        return result.get('results', [])

    def get_dhcp_servers(self) -> List[dict]:
        """Get DHCP server configuration"""
        result = self._safe_get('cmdb/system.dhcp/server')
        return result.get('results', [])

    def get_syslog_settings(self) -> dict:
        """Get syslog settings"""
        return self._safe_get_single('cmdb/log.syslogd/setting')

    def get_certificates(self) -> List[dict]:
        """Get local certificates"""
        result = self._safe_get('cmdb/certificate/local')
        return result.get('results', [])

    def get_sdwan_zones(self) -> List[dict]:
        """Get SD-WAN zones"""
        return self._safe_get_single('cmdb/system/sdwan').get('zone', [])

    def get_sdwan_rules(self) -> List[dict]:
        """Get SD-WAN rules"""
        return self._safe_get_single('cmdb/system/sdwan').get('service', [])

    def get_ha_config(self) -> dict:
        """Get HA configuration"""
        return self._safe_get_single('cmdb/system/ha')


class EnhancedParser:
    """Enhanced parser with additional feature support"""
    
    def __init__(self, enhanced_api: EnhancedFortiGateAPI):
        self.api = enhanced_api
        self.ipv6_addresses: Dict[str, IPv6Address] = {}
        self.ipv6_policies: List = []
        self.ipsec_phase1: Dict[str, IPsecPhase1] = {}
        self.ipsec_phase2: Dict[str, IPsecPhase2] = {}
        self.ospf_config: Optional[OSPFConfig] = None
        self.bgp_config: Optional[BGPConfig] = None
        self.local_users: Dict[str, LocalUser] = {}
        self.user_groups: Dict[str, UserGroup] = {}
        self.radius_servers: Dict[str, RadiusServer] = {}
        self.security_profiles: List[SecurityProfile] = []
        self.migration_tasks: List[MigrationTask] = []
    
    def parse_all_enhanced_features(self):
        """Parse all enhanced features"""
        print("\n=== Enhanced Feature Discovery ===")
        self._parse_ipv6()
        self._parse_vpn()
        self._parse_routing()
        self._parse_users()
        self._parse_security_profiles()
        self._generate_migration_tasks()
    
    def _parse_ipv6(self):
        """Parse IPv6 configuration"""
        print("  - Discovering IPv6 configuration...")
        
        # IPv6 addresses
        ipv6_addrs = self.api.get_ipv6_addresses()
        for addr in ipv6_addrs:
            name = addr.get('name')
            addr_type = addr.get('type', 'ip6-mask')
            
            ipv6_obj = IPv6Address(
                name=name,
                type=addr_type,
                comment=addr.get('comment')
            )
            
            if addr_type == 'ip6-mask':
                ipv6_obj.ip6 = addr.get('ip6')
            elif addr_type == 'ip6-range':
                ipv6_obj.ip6_range = (addr.get('start-ip'), addr.get('end-ip'))
            
            self.ipv6_addresses[name] = ipv6_obj
        
        # IPv6 policies
        self.ipv6_policies = self.api.get_ipv6_policies()
        
        print(f"    Found: {len(self.ipv6_addresses)} IPv6 addresses, {len(self.ipv6_policies)} IPv6 policies")
    
    def _parse_vpn(self):
        """Parse VPN configuration"""
        print("  - Discovering VPN configuration...")
        
        # IPsec Phase 1
        phase1_list = self.api.get_ipsec_phase1()
        for p1 in phase1_list:
            name = p1.get('name')
            phase1 = IPsecPhase1(
                name=name,
                interface=p1.get('interface', ''),
                ike_version=str(p1.get('ike-version', 2)),
                peertype=p1.get('peertype', 'any'),
                remote_gw=p1.get('remote-gw', ''),
                proposal=p1.get('proposal', 'aes128-sha256').split(),
                dhgrp=[int(x) for x in str(p1.get('dhgrp', '14')).split()],
                authmethod=p1.get('authmethod', 'psk'),
                psksecret=p1.get('psksecret'),
                certificate=p1.get('certificate'),
                dpd=p1.get('dpd', 'on-demand'),
                comment=p1.get('comments')
            )
            self.ipsec_phase1[name] = phase1
        
        # IPsec Phase 2
        phase2_list = self.api.get_ipsec_phase2()
        for p2 in phase2_list:
            name = p2.get('name')
            phase2 = IPsecPhase2(
                name=name,
                phase1name=p2.get('phase1name', ''),
                proposal=p2.get('proposal', 'aes128-sha1').split(),
                dhgrp=[int(x) for x in str(p2.get('dhgrp', '14')).split()],
                src_subnet=[p2.get('src-subnet', '0.0.0.0/0')],
                dst_subnet=[p2.get('dst-subnet', '0.0.0.0/0')],
                pfs=p2.get('pfs', 'enable'),
                comment=p2.get('comments')
            )
            self.ipsec_phase2[name] = phase2
        
        print(f"    Found: {len(self.ipsec_phase1)} Phase1, {len(self.ipsec_phase2)} Phase2 tunnels")
    
    def _parse_routing(self):
        """Parse dynamic routing configuration"""
        print("  - Discovering routing protocols...")
        
        # OSPF
        ospf_data = self.api.get_ospf_config()
        if ospf_data and ospf_data.get('router-id'):
            self.ospf_config = OSPFConfig(
                router_id=ospf_data.get('router-id', ''),
                areas=ospf_data.get('area', []),
                networks=ospf_data.get('network', []),
                redistribute=ospf_data.get('redistribute', [])
            )
        
        # BGP
        bgp_data = self.api.get_bgp_config()
        if bgp_data and bgp_data.get('as'):
            self.bgp_config = BGPConfig(
                as_number=str(bgp_data.get('as', '')),
                router_id=bgp_data.get('router-id', ''),
                neighbors=bgp_data.get('neighbor', []),
                networks=bgp_data.get('network', []),
                redistribute=bgp_data.get('redistribute', [])
            )
        
        ospf_status = "Configured" if self.ospf_config else "Not configured"
        bgp_status = "Configured" if self.bgp_config else "Not configured"
        print(f"    OSPF: {ospf_status}, BGP: {bgp_status}")
    
    def _parse_users(self):
        """Parse user and authentication configuration"""
        print("  - Discovering user configuration...")
        
        # Local users
        users = self.api.get_local_users()
        for user in users:
            name = user.get('name')
            self.local_users[name] = LocalUser(
                name=name,
                type=user.get('type', 'password'),
                status=user.get('status', 'enable'),
                comment=user.get('comments')
            )
        
        # User groups
        groups = self.api.get_user_groups()
        for group in groups:
            name = group.get('name')
            members = [m.get('name') for m in group.get('member', [])]
            self.user_groups[name] = UserGroup(
                name=name,
                members=members,
                comment=group.get('comments')
            )
        
        # RADIUS servers
        radius_list = self.api.get_radius_servers()
        for radius in radius_list:
            name = radius.get('name')
            self.radius_servers[name] = RadiusServer(
                name=name,
                server=radius.get('server', ''),
                secret=radius.get('secret', ''),
                auth_type=radius.get('auth-type', 'auto'),
                timeout=radius.get('timeout', 5)
            )
        
        print(f"    Found: {len(self.local_users)} users, {len(self.user_groups)} groups, {len(self.radius_servers)} RADIUS servers")
    
    def _parse_security_profiles(self):
        """Analyze security profiles"""
        print("  - Analyzing security profiles...")
        
        # Antivirus
        av_profiles = self.api.get_antivirus_profiles()
        for av in av_profiles:
            profile = SecurityProfile(
                type='antivirus',
                name=av.get('name'),
                settings=av,
                policies_using=[]
            )
            self.security_profiles.append(profile)
        
        # IPS
        ips_profiles = self.api.get_ips_sensors()
        for ips in ips_profiles:
            profile = SecurityProfile(
                type='ips',
                name=ips.get('name'),
                settings=ips,
                policies_using=[]
            )
            self.security_profiles.append(profile)
        
        # Web Filter
        wf_profiles = self.api.get_webfilter_profiles()
        for wf in wf_profiles:
            profile = SecurityProfile(
                type='webfilter',
                name=wf.get('name'),
                settings=wf,
                policies_using=[]
            )
            self.security_profiles.append(profile)
        
        print(f"    Found: {len(self.security_profiles)} security profiles")
    
    def _generate_migration_tasks(self):
        """Generate manual migration tasks"""
        print("  - Generating migration task list...")
        
        # VPN tasks
        if self.ipsec_phase1:
            for name, p1 in self.ipsec_phase1.items():
                task = MigrationTask(
                    category="VPN",
                    priority="high",
                    title=f"Migrate IPsec VPN: {name}",
                    description=f"Configure IPsec tunnel from FortiGate to Palo Alto",
                    fortigate_config=json.dumps(vars(p1), indent=2),
                    palo_alto_steps=[
                        f"1. Create IKE Gateway: {name}_gw",
                        f"   - Peer Address: {p1.remote_gw}",
                        f"   - IKE version: {p1.ike_version}",
                        f"   - Pre-shared Key: <use from FortiGate>",
                        f"2. Create IKE Crypto Profile matching proposals",
                        f"3. Create IPsec Crypto Profile for Phase 2",
                        f"4. Create IPsec Tunnel interface",
                        f"5. Create tunnel zone and add tunnel interface",
                        f"6. Create proxy-IDs if needed"
                    ],
                    reference_docs=[
                        "https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/vpn"
                    ],
                    estimated_time="30-45 minutes per tunnel"
                )
                self.migration_tasks.append(task)
        
        # Security profile tasks
        if self.security_profiles:
            for profile in self.security_profiles:
                task = MigrationTask(
                    category="Security Profiles",
                    priority="medium",
                    title=f"Create {profile.type.upper()} profile: {profile.name}",
                    description=f"Manually configure {profile.type} security profile",
                    fortigate_config=json.dumps(profile.settings, indent=2, default=str)[:500] + "...",
                    palo_alto_steps=self._get_security_profile_steps(profile.type),
                    reference_docs=[
                        f"https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/threat-prevention"
                    ],
                    estimated_time="15-30 minutes per profile"
                )
                self.migration_tasks.append(task)
        
        # OSPF task
        if self.ospf_config:
            task = MigrationTask(
                category="Routing",
                priority="high",
                title="Configure OSPF",
                description="Set up OSPF routing protocol",
                fortigate_config=json.dumps(vars(self.ospf_config), indent=2, default=str),
                palo_alto_steps=[
                    "1. Configure virtual router",
                    f"2. Set router-ID: {self.ospf_config.router_id}",
                    "3. Create OSPF areas",
                    "4. Add interfaces to areas",
                    "5. Configure redistribution if needed",
                    "6. Set authentication if used"
                ],
                reference_docs=[
                    "https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/networking/configure-ospf"
                ],
                estimated_time="45-60 minutes"
            )
            self.migration_tasks.append(task)
        
        # BGP task
        if self.bgp_config:
            task = MigrationTask(
                category="Routing",
                priority="high",
                title="Configure BGP",
                description="Set up BGP routing protocol",
                fortigate_config=json.dumps(vars(self.bgp_config), indent=2, default=str),
                palo_alto_steps=[
                    "1. Configure virtual router",
                    f"2. Set AS number: {self.bgp_config.as_number}",
                    f"3. Set router-ID: {self.bgp_config.router_id}",
                    "4. Configure BGP peer groups",
                    "5. Add neighbors with authentication",
                    "6. Configure route redistribution",
                    "7. Set route-maps/filters"
                ],
                reference_docs=[
                    "https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/networking/configure-bgp"
                ],
                estimated_time="60-90 minutes"
            )
            self.migration_tasks.append(task)
        
        print(f"    Generated: {len(self.migration_tasks)} migration tasks")
    
    def _get_security_profile_steps(self, profile_type: str) -> List[str]:
        """Get steps for security profile migration"""
        if profile_type == 'antivirus':
            return [
                "1. Objects > Security Profiles > Antivirus",
                "2. Click Add to create new profile",
                "3. Configure decoder settings (HTTP, SMTP, IMAP, POP3, FTP, SMB)",
                "4. Set action for each protocol (default, allow, alert, block, reset)",
                "5. Enable WildFire analysis for unknown files",
                "6. Set packet capture for malicious files if needed",
                "7. Apply to security policies"
            ]
        elif profile_type == 'ips':
            return [
                "1. Objects > Security Profiles > Vulnerability Protection",
                "2. Click Add to create new profile",
                "3. Select threat severity levels to block",
                "4. Configure exception list if needed",
                "5. Enable packet capture for threats",
                "6. Consider enabling strict policy",
                "7. Apply to security policies"
            ]
        elif profile_type == 'webfilter':
            return [
                "1. Objects > Security Profiles > URL Filtering",
                "2. Click Add to create new profile",
                "3. Configure URL category actions",
                "4. Add custom URL lists if needed",
                "5. Configure credential detection",
                "6. Set up safe search enforcement",
                "7. Enable HTTP header logging",
                "8. Apply to security policies"
            ]
        return []


class MigrationReportGenerator:
    """Generate comprehensive migration reports"""
    
    def __init__(self, base_parser, enhanced_parser: EnhancedParser):
        self.base = base_parser
        self.enhanced = enhanced_parser
    
    def generate_full_report(self, output_file: str = "migration_report.md"):
        """Generate complete migration report"""
        sections = []
        
        sections.append(self._generate_header())
        sections.append(self._generate_summary())
        sections.append(self._generate_automated_section())
        sections.append(self._generate_manual_tasks())
        sections.append(self._generate_vpn_worksheet())
        sections.append(self._generate_routing_worksheet())
        sections.append(self._generate_security_profile_guide())
        sections.append(self._generate_validation_checklist())
        sections.append(self._generate_rollback_plan())
        
        report = "\n\n".join(sections)
        
        with open(output_file, 'w') as f:
            f.write(report)
        
        return output_file
    
    def _generate_header(self) -> str:
        """Generate report header"""
        return """# FortiGate to Palo Alto Networks Migration Report

**Generated:** {date}
**Migration Tool Version:** 2.0 Enhanced

---
""".format(date=__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def _generate_summary(self) -> str:
        """Generate executive summary"""
        total_policies = len(self.base.policies)
        total_addr = len(self.base.addresses) + len(self.base.address_groups)
        total_svc = len(self.base.services) + len(self.base.service_groups)
        total_nat = len(self.base.nat_pools) + len(self.base.vips)
        
        vpn_count = len(self.enhanced.ipsec_phase1)
        ipv6_count = len(self.enhanced.ipv6_addresses) + len(self.enhanced.ipv6_policies)
        manual_tasks = len(self.enhanced.migration_tasks)
        
        return f"""## Executive Summary

### Configuration Overview
- **IPv4 Policies:** {total_policies}
- **IPv6 Policies:** {len(self.enhanced.ipv6_policies)}
- **Address Objects:** {total_addr}
- **Service Objects:** {total_svc}
- **NAT Configuration:** {total_nat}
- **IPsec VPN Tunnels:** {vpn_count}
- **OSPF:** {"Configured" if self.enhanced.ospf_config else "Not configured"}
- **BGP:** {"Configured" if self.enhanced.bgp_config else "Not configured"}

### Migration Status
✅ **Automated:** Core firewall policies, objects, NAT, static routes
⚠️ **Semi-Automated:** IPv6 configuration, VPN templates generated
📋 **Manual Required:** {manual_tasks} tasks identified (see Manual Tasks section)

### Estimated Migration Time
- **Automated deployment:** 30-45 minutes
- **Manual configuration:** {manual_tasks * 30} - {manual_tasks * 45} minutes
- **Testing and validation:** 2-4 hours
- **Total estimated time:** 4-8 hours

---"""
    
    def _generate_automated_section(self) -> str:
        """Generate automated migration section"""
        return """## Automated Migration Components

The following configurations have been automatically converted to Terraform:

### ✅ Fully Automated
- [x] IPv4 address objects and groups
- [x] Service objects and groups  
- [x] IPv4 security policies (allow/deny rules)
- [x] NAT policies (source and destination)
- [x] Virtual IPs and port forwarding
- [x] IP pools
- [x] Static routes
- [x] Zones and interfaces (basic configuration)

### ⚠️ Partially Automated  
- [x] IPv6 address objects (Terraform generated, review required)
- [x] IPv6 policies (Terraform generated, review required)
- [x] VPN configuration (templates generated, manual configuration required)
- [x] Security profiles (analysis complete, manual creation required)

### Instructions for Automated Deployment

1. Review generated Terraform file: `palo_alto.tf`
2. Verify provider configuration
3. Initialize Terraform:
   ```bash
   terraform init
   ```
4. Review planned changes:
   ```bash
   terraform plan -out=migration.plan
   ```
5. Apply configuration:
   ```bash
   terraform apply migration.plan
   ```

---"""
    
    def _generate_manual_tasks(self) -> str:
        """Generate manual tasks section"""
        if not self.enhanced.migration_tasks:
            return """## Manual Migration Tasks

No manual tasks required. All configuration has been automated.

---"""
        
        output = ["## Manual Migration Tasks\n"]
        output.append("The following tasks require manual configuration in Palo Alto Networks:\n")
        
        # Group by category
        by_category = {}
        for task in self.enhanced.migration_tasks:
            if task.category not in by_category:
                by_category[task.category] = []
            by_category[task.category].append(task)
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        task_number = 1
        for category in sorted(by_category.keys()):
            output.append(f"\n### {category}\n")
            
            tasks = sorted(by_category[category], 
                         key=lambda x: priority_order.get(x.priority, 99))
            
            for task in tasks:
                output.append(f"\n#### Task {task_number}: {task.title}\n")
                output.append(f"**Priority:** {task.priority.upper()}\n")
                output.append(f"**Estimated Time:** {task.estimated_time}\n")
                output.append(f"\n**Description:** {task.description}\n")
                
                if task.palo_alto_steps:
                    output.append("\n**Configuration Steps:**\n")
                    for step in task.palo_alto_steps:
                        output.append(f"   {step}\n")
                
                if task.reference_docs:
                    output.append("\n**Reference Documentation:**\n")
                    for doc in task.reference_docs:
                        output.append(f"- {doc}\n")
                
                task_number += 1
        
        output.append("\n---")
        return "".join(output)
    
    def _generate_vpn_worksheet(self) -> str:
        """Generate VPN configuration worksheet"""
        if not self.enhanced.ipsec_phase1:
            return ""
        
        output = ["## VPN Migration Worksheet\n"]
        output.append("### IPsec VPN Tunnels\n")
        
        for name, p1 in self.enhanced.ipsec_phase1.items():
            p2_list = [p2 for p2 in self.enhanced.ipsec_phase2.values() 
                      if p2.phase1name == name]
            
            output.append(f"\n#### Tunnel: {name}\n")
            output.append("```\n")
            output.append(f"Remote Gateway: {p1.remote_gw}\n")
            output.append(f"Interface: {p1.interface}\n")
            output.append(f"IKE Version: {p1.ike_version}\n")
            output.append(f"Authentication: {p1.authmethod}\n")
            output.append(f"Proposals: {', '.join(p1.proposal)}\n")
            output.append(f"DH Groups: {', '.join(map(str, p1.dhgrp))}\n")
            output.append("```\n")
            
            output.append("\n**Palo Alto Configuration:**\n")
            output.append("```hcl\n")
            output.append(f"# IKE Gateway\n")
            output.append(f"resource \"panos_ike_gateway\" \"{name}_gw\" {{\n")
            output.append(f"  name           = \"{name}_gw\"\n")
            output.append(f"  version        = \"ikev{p1.ike_version}\"\n")
            output.append(f"  peer_ip_type   = \"ip\"\n")
            output.append(f"  peer_ip_value  = \"{p1.remote_gw}\"\n")
            output.append(f"  interface      = \"{p1.interface}\"\n")
            output.append(f"  auth_type      = \"pre-shared-key\"\n")
            output.append(f"  pre_shared_key = \"<INSERT_PSK_HERE>\"\n")
            output.append(f"}}\n")
            output.append("```\n")
            
            if p2_list:
                output.append(f"\n**Phase 2 Selectors:**\n")
                for p2 in p2_list:
                    output.append(f"- Local: {', '.join(p2.src_subnet)}\n")
                    output.append(f"- Remote: {', '.join(p2.dst_subnet)}\n")
        
        output.append("\n---")
        return "".join(output)
    
    def _generate_routing_worksheet(self) -> str:
        """Generate routing configuration worksheet"""
        output = []
        
        if self.enhanced.ospf_config:
            output.append("## OSPF Configuration Worksheet\n")
            output.append("```\n")
            output.append(f"Router ID: {self.enhanced.ospf_config.router_id}\n")
            output.append(f"Areas: {len(self.enhanced.ospf_config.areas)}\n")
            output.append("```\n\n")
            output.append("**Palo Alto Steps:**\n")
            output.append("1. Network > Virtual Routers > [select VR]\n")
            output.append("2. OSPF > Enable\n")
            output.append(f"3. Set Router ID: {self.enhanced.ospf_config.router_id}\n")
            output.append("4. Configure areas and add interfaces\n")
            output.append("5. Set authentication if required\n")
            output.append("6. Configure redistribution\n\n")
        
        if self.enhanced.bgp_config:
            output.append("## BGP Configuration Worksheet\n")
            output.append("```\n")
            output.append(f"AS Number: {self.enhanced.bgp_config.as_number}\n")
            output.append(f"Router ID: {self.enhanced.bgp_config.router_id}\n")
            output.append(f"Neighbors: {len(self.enhanced.bgp_config.neighbors)}\n")
            output.append("```\n\n")
            output.append("**Palo Alto Steps:**\n")
            output.append("1. Network > Virtual Routers > [select VR]\n")
            output.append("2. BGP > Enable\n")
            output.append(f"3. Set AS: {self.enhanced.bgp_config.as_number}\n")
            output.append(f"4. Set Router ID: {self.enhanced.bgp_config.router_id}\n")
            output.append("5. Configure peer groups\n")
            output.append("6. Add neighbors with authentication\n")
            output.append("7. Configure import/export policies\n\n")
        
        if output:
            output.append("---")
            return "".join(output)
        return ""
    
    def _generate_security_profile_guide(self) -> str:
        """Generate security profile configuration guide"""
        if not self.enhanced.security_profiles:
            return ""
        
        output = ["## Security Profiles Configuration Guide\n"]
        output.append("### Overview\n")
        output.append(f"Total profiles detected: {len(self.enhanced.security_profiles)}\n\n")
        
        profile_types = {}
        for profile in self.enhanced.security_profiles:
            if profile.type not in profile_types:
                profile_types[profile.type] = []
            profile_types[profile.type].append(profile.name)
        
        for ptype, names in profile_types.items():
            output.append(f"\n### {ptype.upper()} Profiles\n")
            output.append(f"Profiles to migrate: {len(names)}\n")
            for name in names:
                output.append(f"- {name}\n")
        
        output.append("\n### Best Practices\n")
        output.append("1. Start with Palo Alto's best practice profiles\n")
        output.append("2. Customize based on FortiGate settings\n")
        output.append("3. Test in monitoring mode before enforcement\n")
        output.append("4. Enable threat logging and WildFire analysis\n")
        output.append("5. Review and tune based on false positives\n")
        
        output.append("\n---")
        return "".join(output)
    
    def _generate_validation_checklist(self) -> str:
        """Generate validation checklist"""
        return """## Post-Migration Validation Checklist

### Phase 1: Configuration Verification
- [ ] All address objects imported successfully
- [ ] All service objects created correctly
- [ ] Security policies match FortiGate policy count
- [ ] NAT policies configured and ordered correctly
- [ ] Zones created and interfaces assigned
- [ ] Static routes configured with correct metrics
- [ ] VPN tunnels established (if applicable)
- [ ] Routing protocols operational (OSPF/BGP)

### Phase 2: Connectivity Testing
- [ ] Internal to internal communication works
- [ ] Internal to internet access functional
- [ ] Inbound port forwarding operational
- [ ] VPN tunnel traffic passing (if applicable)
- [ ] Application visibility working
- [ ] DNS resolution functioning

### Phase 3: Security Validation
- [ ] Default deny rule blocking unauthorized traffic
- [ ] Security profiles blocking threats (if enabled)
- [ ] URL filtering operational (if configured)
- [ ] IPS/IDS detecting attacks (if configured)
- [ ] Logs being generated correctly
- [ ] Threat intelligence updates working

### Phase 4: Performance Verification
- [ ] Latency within acceptable range
- [ ] Throughput meeting requirements
- [ ] Session count appropriate
- [ ] CPU/memory utilization normal
- [ ] No packet drops observed

### Testing Commands

**Test security policy match:**
```
test security-policy-match source 192.168.1.10 destination 8.8.8.8 protocol 6 destination-port 443
```

**Test NAT policy match:**
```
test nat-policy-match source 192.168.1.10 destination 8.8.8.8 protocol 6 destination-port 443
```

**Verify routes:**
```
show routing route
show routing protocol ospf summary
show routing protocol bgp summary
```

**Check VPN status:**
```
show vpn ike-sa
show vpn ipsec-sa
```

---"""
    
    def _generate_rollback_plan(self) -> str:
        """Generate rollback plan"""
        return """## Rollback Plan

### Emergency Rollback Procedure

If critical issues are discovered post-migration:

#### Option 1: Terraform Destroy
```bash
terraform destroy
# Confirm with 'yes'
# This removes all PA configuration
# Switch traffic back to FortiGate
```

#### Option 2: Disable PA Device
1. Leave FortiGate in place during migration
2. If issues occur, route traffic back to FortiGate
3. Troubleshoot PA configuration offline
4. Re-cutover when ready

#### Option 3: Restore from Backup
```bash
# Restore PA configuration from backup
# Via GUI: Device > Setup > Operations > Import
# Select previous running-config.xml
```

### Mitigation Strategies

**Before Migration:**
- Take full FortiGate configuration backup
- Document current FortiGate policy hit counts
- Export PA running config before changes
- Have console access to both devices
- Prepare maintenance window communication

**During Migration:**
- Deploy during low-traffic window
- Monitor traffic flows actively
- Keep FortiGate available for quick rollback
- Have experienced staff available

**After Migration:**
- Monitor for 48-72 hours closely
- Review logs for anomalies
- Compare traffic patterns with baseline
- Document any issues and resolutions

---

## Support and Resources

**Palo Alto Resources:**
- Documentation: https://docs.paloaltonetworks.com
- Live Community: https://live.paloaltonetworks.com
- Support Portal: https://support.paloaltonetworks.com

**Migration Resources:**
- Expedition Tool: https://live.paloaltonetworks.com/expedition
- Best Practices: https://www.paloaltonetworks.com/resources/techbriefs
- Training: https://www.paloaltonetworks.com/services/education

---

*End of Migration Report*
"""

# Export classes for use in main script
__all__ = [
    'EnhancedFortiGateAPI',
    'EnhancedParser',
    'MigrationReportGenerator',
    'IPv6Address',
    'IPsecPhase1',
    'IPsecPhase2',
    'OSPFConfig',
    'BGPConfig',
    'LocalUser',
    'UserGroup',
    'RadiusServer',
    'SecurityProfile',
    'MigrationTask'
]
