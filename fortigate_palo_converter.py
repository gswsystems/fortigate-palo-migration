#!/usr/bin/env python3
"""
FortiGate to Palo Alto Networks Terraform Converter
Converts FortiGate configuration to Terraform using panos provider
Fetches configuration via FortiGate REST API

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

import requests
import urllib3
import sys
import argparse
import ipaddress
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class AddressObject:
    """Represents a FortiGate address object"""
    name: str
    type: str  # ipmask, iprange, fqdn, geography, wildcard, dynamic
    subnet: Optional[str] = None
    ip_range: Optional[Tuple[str, str]] = None
    fqdn: Optional[str] = None
    country: Optional[str] = None
    interface: Optional[str] = None
    comment: Optional[str] = None
    wildcard: Optional[str] = None
    members: List[str] = field(default_factory=list)  # For address groups
    uuid: Optional[str] = None


@dataclass
class ServiceObject:
    """Represents a FortiGate service object"""
    name: str
    protocol: str
    tcp_portrange: Optional[str] = None
    udp_portrange: Optional[str] = None
    icmp_type: Optional[int] = None
    icmp_code: Optional[int] = None
    sctp_portrange: Optional[str] = None
    protocol_number: Optional[int] = None
    comment: Optional[str] = None
    members: List[str] = field(default_factory=list)  # For service groups


@dataclass
class FirewallPolicy:
    """Represents a FortiGate firewall policy"""
    policyid: str
    name: str
    srcintf: List[str]
    dstintf: List[str]
    srcaddr: List[str]
    dstaddr: List[str]
    service: List[str]
    action: str
    schedule: str = "always"
    status: str = "enable"
    nat: str = "disable"
    poolname: List[str] = field(default_factory=list)
    ippool: str = "disable"
    comments: Optional[str] = None
    logtraffic: str = "utm"
    log_traffic_start: str = "disable"
    av_profile: Optional[str] = None
    webfilter_profile: Optional[str] = None
    application_list: Optional[str] = None
    ips_sensor: Optional[str] = None
    ssl_ssh_profile: Optional[str] = None
    profile_group: Optional[str] = None
    uuid: Optional[str] = None


@dataclass
class NATPool:
    """Represents a FortiGate IP pool"""
    name: str
    type: str  # overload, one-to-one, fixed-port-range, port-block-allocation
    startip: str
    endip: str
    arp_reply: str = "enable"
    comments: Optional[str] = None


@dataclass
class VIP:
    """Represents a FortiGate Virtual IP"""
    name: str
    extip: str
    mappedip: str
    extintf: str
    portforward: str = "disable"
    protocol: Optional[str] = None
    extport: Optional[str] = None
    mappedport: Optional[str] = None
    comment: Optional[str] = None
    type: str = "static-nat"


@dataclass
class StaticRoute:
    """Represents a FortiGate static route"""
    seq_num: str
    dst: str
    gateway: str
    device: str
    distance: int = 10
    priority: int = 0
    comment: Optional[str] = None


@dataclass
class Interface:
    """Represents a FortiGate interface"""
    name: str
    vdom: str
    ip: Optional[str] = None
    type: str = "physical"
    vlanid: Optional[int] = None
    interface: Optional[str] = None  # Parent interface for VLANs
    mode: str = "static"
    status: str = "up"
    alias: Optional[str] = None


class FortiGateAPI:
    """FortiGate REST API client"""
    
    def __init__(self, host: str, api_key: str = None, username: str = None, 
                 password: str = None, vdom: str = "root", verify_ssl: bool = False):
        host = host.rstrip('/')
        if not host.startswith(('http://', 'https://')):
            host = f"https://{host}"
        self.host = host
        self.api_key = api_key
        self.username = username
        self.password = password
        self.vdom = vdom
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        # Set up authentication
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
        elif username and password:
            self._login()
    
    def _login(self):
        """Login using username/password"""
        login_url = f"{self.host}/logincheck"
        data = {
            'username': self.username,
            'secretkey': self.password
        }
        response = self.session.post(login_url, data=data)
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code}")
    
    def get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to FortiGate API"""
        url = f"{self.host}/api/v2/{endpoint}"
        
        if params is None:
            params = {}
        params['vdom'] = self.vdom
        
        response = self.session.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_addresses(self) -> List[dict]:
        """Get all firewall addresses"""
        result = self.get('cmdb/firewall/address')
        return result.get('results', [])
    
    def get_address_groups(self) -> List[dict]:
        """Get all firewall address groups"""
        result = self.get('cmdb/firewall/addrgrp')
        return result.get('results', [])
    
    def get_services(self) -> List[dict]:
        """Get all custom firewall services"""
        result = self.get('cmdb/firewall.service/custom')
        return result.get('results', [])
    
    def get_service_groups(self) -> List[dict]:
        """Get all firewall service groups"""
        result = self.get('cmdb/firewall.service/group')
        return result.get('results', [])
    
    def get_policies(self) -> List[dict]:
        """Get all firewall policies"""
        result = self.get('cmdb/firewall/policy')
        return result.get('results', [])
    
    def get_ipv6_policies(self) -> List[dict]:
        """Get all IPv6 firewall policies"""
        result = self.get('cmdb/firewall/policy6')
        return result.get('results', [])
    
    def get_nat_pools(self) -> List[dict]:
        """Get all IP pools"""
        result = self.get('cmdb/firewall/ippool')
        return result.get('results', [])
    
    def get_vips(self) -> List[dict]:
        """Get all Virtual IPs"""
        result = self.get('cmdb/firewall/vip')
        return result.get('results', [])
    
    def get_vip_groups(self) -> List[dict]:
        """Get all VIP groups"""
        result = self.get('cmdb/firewall/vipgrp')
        return result.get('results', [])
    
    def get_static_routes(self) -> List[dict]:
        """Get all static routes"""
        result = self.get('cmdb/router/static')
        return result.get('results', [])
    
    def get_interfaces(self) -> List[dict]:
        """Get all interfaces"""
        result = self.get('cmdb/system/interface')
        return result.get('results', [])
    
    def get_zones(self) -> List[dict]:
        """Get all zones"""
        result = self.get('cmdb/system/zone')
        return result.get('results', [])


class FortiGateParser:
    """Parser for FortiGate configuration via API"""
    
    def __init__(self, api: FortiGateAPI):
        self.api = api
        self.addresses: Dict[str, AddressObject] = {}
        self.address_groups: Dict[str, AddressObject] = {}
        self.services: Dict[str, ServiceObject] = {}
        self.service_groups: Dict[str, ServiceObject] = {}
        self.policies: List[FirewallPolicy] = []
        self.nat_pools: Dict[str, NATPool] = {}
        self.vips: Dict[str, VIP] = {}
        self.vip_groups: Dict[str, List[str]] = {}
        self.static_routes: List[StaticRoute] = []
        self.interfaces: Dict[str, Interface] = {}
        self.zones: Dict[str, List[str]] = {}
        
    def parse(self):
        """Main parsing function"""
        print("Fetching configuration from FortiGate...")
        self._parse_addresses()
        self._parse_address_groups()
        self._parse_services()
        self._parse_service_groups()
        self._parse_nat_pools()
        self._parse_vips()
        self._parse_vip_groups()
        self._parse_policies()
        self._parse_static_routes()
        self._parse_interfaces()
        self._parse_zones()
        print("Configuration fetched successfully")
    
    def _parse_addresses(self):
        """Parse address objects from API"""
        print("  - Fetching addresses...")
        addresses_data = self.api.get_addresses()
        
        for addr_data in addresses_data:
            name = addr_data.get('name', '')
            addr_type = addr_data.get('type', 'ipmask')
            
            addr = AddressObject(
                name=name,
                type=addr_type,
                comment=addr_data.get('comment'),
                interface=addr_data.get('associated-interface'),
                uuid=addr_data.get('uuid')
            )
            
            if addr_type == 'ipmask':
                subnet = addr_data.get('subnet', '').split()
                if len(subnet) == 2:
                    ip, mask = subnet
                    try:
                        network = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
                        addr.subnet = str(network)
                    except:
                        addr.subnet = f"{ip}/{mask}"
            
            elif addr_type == 'iprange':
                addr.ip_range = (
                    addr_data.get('start-ip'),
                    addr_data.get('end-ip')
                )
            
            elif addr_type == 'fqdn':
                addr.fqdn = addr_data.get('fqdn')
            
            elif addr_type == 'geography':
                addr.country = addr_data.get('country')
            
            elif addr_type == 'wildcard':
                wildcard = addr_data.get('wildcard', '').split()
                if len(wildcard) == 2:
                    addr.wildcard = f"{wildcard[0]}/{wildcard[1]}"
            
            self.addresses[name] = addr
        
        print(f"    Found {len(self.addresses)} addresses")
    
    def _parse_address_groups(self):
        """Parse address groups from API"""
        print("  - Fetching address groups...")
        groups_data = self.api.get_address_groups()
        
        for group_data in groups_data:
            name = group_data.get('name', '')
            
            group = AddressObject(
                name=name,
                type='group',
                comment=group_data.get('comment'),
                uuid=group_data.get('uuid')
            )
            
            members = group_data.get('member', [])
            group.members = [m.get('name') for m in members if isinstance(m, dict)]
            
            self.address_groups[name] = group
        
        print(f"    Found {len(self.address_groups)} address groups")
    
    def _parse_services(self):
        """Parse service objects from API"""
        print("  - Fetching services...")
        services_data = self.api.get_services()
        
        for svc_data in services_data:
            name = svc_data.get('name', '')
            protocol = svc_data.get('protocol', 'TCP/UDP/SCTP')
            
            svc = ServiceObject(
                name=name,
                protocol=protocol,
                comment=svc_data.get('comment')
            )
            
            # Parse port ranges
            svc.tcp_portrange = svc_data.get('tcp-portrange')
            svc.udp_portrange = svc_data.get('udp-portrange')
            svc.sctp_portrange = svc_data.get('sctp-portrange')
            
            # Parse ICMP
            svc.icmp_type = svc_data.get('icmptype')
            svc.icmp_code = svc_data.get('icmpcode')
            
            # Parse IP protocol number
            svc.protocol_number = svc_data.get('protocol-number')
            
            self.services[name] = svc
        
        print(f"    Found {len(self.services)} services")
    
    def _parse_service_groups(self):
        """Parse service groups from API"""
        print("  - Fetching service groups...")
        groups_data = self.api.get_service_groups()
        
        for group_data in groups_data:
            name = group_data.get('name', '')
            
            group = ServiceObject(
                name=name,
                protocol='group',
                comment=group_data.get('comment')
            )
            
            members = group_data.get('member', [])
            group.members = [m.get('name') for m in members if isinstance(m, dict)]
            
            self.service_groups[name] = group
        
        print(f"    Found {len(self.service_groups)} service groups")
    
    def _parse_nat_pools(self):
        """Parse NAT pools from API"""
        print("  - Fetching IP pools...")
        pools_data = self.api.get_nat_pools()
        
        for pool_data in pools_data:
            name = pool_data.get('name', '')
            
            pool = NATPool(
                name=name,
                type=pool_data.get('type', 'overload'),
                startip=pool_data.get('startip', ''),
                endip=pool_data.get('endip', ''),
                comments=pool_data.get('comments'),
                arp_reply=pool_data.get('arp-reply', 'enable')
            )
            
            self.nat_pools[name] = pool
        
        print(f"    Found {len(self.nat_pools)} IP pools")
    
    def _parse_vips(self):
        """Parse Virtual IPs from API"""
        print("  - Fetching VIPs...")
        vips_data = self.api.get_vips()
        
        for vip_data in vips_data:
            name = vip_data.get('name', '')
            
            vip = VIP(
                name=name,
                extip=vip_data.get('extip', ''),
                mappedip=vip_data.get('mappedip', ''),
                extintf=vip_data.get('extintf', 'any'),
                portforward=vip_data.get('portforward', 'disable'),
                protocol=vip_data.get('protocol'),
                extport=vip_data.get('extport'),
                mappedport=vip_data.get('mappedport'),
                comment=vip_data.get('comment'),
                type=vip_data.get('type', 'static-nat')
            )
            
            self.vips[name] = vip
        
        print(f"    Found {len(self.vips)} VIPs")
    
    def _parse_vip_groups(self):
        """Parse VIP groups from API"""
        print("  - Fetching VIP groups...")
        groups_data = self.api.get_vip_groups()
        
        for group_data in groups_data:
            name = group_data.get('name', '')
            members = group_data.get('member', [])
            member_names = [m.get('name') for m in members if isinstance(m, dict)]
            self.vip_groups[name] = member_names
        
        print(f"    Found {len(self.vip_groups)} VIP groups")
    
    def _parse_policies(self):
        """Parse firewall policies from API"""
        print("  - Fetching firewall policies...")
        policies_data = self.api.get_policies()
        
        for pol_data in policies_data:
            policyid = str(pol_data.get('policyid', ''))
            
            policy = FirewallPolicy(
                policyid=policyid,
                name=pol_data.get('name', f"policy_{policyid}"),
                srcintf=[],
                dstintf=[],
                srcaddr=[],
                dstaddr=[],
                service=[],
                action=pol_data.get('action', 'accept'),
                schedule=pol_data.get('schedule', 'always'),
                status=pol_data.get('status', 'enable'),
                nat=pol_data.get('nat', 'disable'),
                ippool=pol_data.get('ippool', 'disable'),
                comments=pol_data.get('comments'),
                logtraffic=pol_data.get('logtraffic', 'utm'),
                log_traffic_start=pol_data.get('logtraffic-start', 'disable'),
                av_profile=pol_data.get('av-profile'),
                webfilter_profile=pol_data.get('webfilter-profile'),
                application_list=pol_data.get('application-list'),
                ips_sensor=pol_data.get('ips-sensor'),
                ssl_ssh_profile=pol_data.get('ssl-ssh-profile'),
                profile_group=pol_data.get('profile-group'),
                uuid=pol_data.get('uuid')
            )
            
            # Parse interfaces
            srcintf = pol_data.get('srcintf', [])
            policy.srcintf = [i.get('name') for i in srcintf if isinstance(i, dict)]
            
            dstintf = pol_data.get('dstintf', [])
            policy.dstintf = [i.get('name') for i in dstintf if isinstance(i, dict)]
            
            # Parse addresses
            srcaddr = pol_data.get('srcaddr', [])
            policy.srcaddr = [a.get('name') for a in srcaddr if isinstance(a, dict)]
            
            dstaddr = pol_data.get('dstaddr', [])
            policy.dstaddr = [a.get('name') for a in dstaddr if isinstance(a, dict)]
            
            # Parse services
            service = pol_data.get('service', [])
            policy.service = [s.get('name') for s in service if isinstance(s, dict)]
            
            # Parse NAT pools
            poolname = pol_data.get('poolname', [])
            policy.poolname = [p.get('name') for p in poolname if isinstance(p, dict)]
            
            self.policies.append(policy)
        
        print(f"    Found {len(self.policies)} policies")
    
    def _parse_static_routes(self):
        """Parse static routes from API"""
        print("  - Fetching static routes...")
        routes_data = self.api.get_static_routes()
        
        for route_data in routes_data:
            route = StaticRoute(
                seq_num=str(route_data.get('seq-num', '0')),
                dst=route_data.get('dst', '0.0.0.0/0'),
                gateway=route_data.get('gateway', ''),
                device=route_data.get('device', ''),
                distance=route_data.get('distance', 10),
                priority=route_data.get('priority', 0),
                comment=route_data.get('comment')
            )
            
            self.static_routes.append(route)
        
        print(f"    Found {len(self.static_routes)} static routes")
    
    def _parse_interfaces(self):
        """Parse interfaces from API"""
        print("  - Fetching interfaces...")
        interfaces_data = self.api.get_interfaces()
        
        for intf_data in interfaces_data:
            name = intf_data.get('name', '')
            
            intf = Interface(
                name=name,
                vdom=intf_data.get('vdom', 'root'),
                ip=intf_data.get('ip'),
                type=intf_data.get('type', 'physical'),
                vlanid=intf_data.get('vlanid'),
                interface=intf_data.get('interface'),
                mode=intf_data.get('mode', 'static'),
                status=intf_data.get('status', 'up'),
                alias=intf_data.get('alias')
            )
            
            self.interfaces[name] = intf
        
        print(f"    Found {len(self.interfaces)} interfaces")
    
    def _parse_zones(self):
        """Parse zones from API"""
        print("  - Fetching zones...")
        zones_data = self.api.get_zones()
        
        for zone_data in zones_data:
            name = zone_data.get('name', '')
            members = zone_data.get('interface', [])
            member_names = [m.get('interface-name') for m in members if isinstance(m, dict)]
            self.zones[name] = member_names
        
        print(f"    Found {len(self.zones)} zones")

class TerraformGenerator:
    """Generate Terraform configuration for Palo Alto Networks"""
    
    def __init__(self, parser: FortiGateParser, device_group: str = "shared",
                 vsys: str = "vsys1", template: str = None):
        self.parser = parser
        self.device_group = device_group
        self.vsys = vsys
        self.template = template
        self.generated_objects: Set[str] = set()
        self.zone_mapping: Dict[str, str] = {}
        
    def sanitize_name(self, name: str) -> str:
        """Sanitize object names for Terraform"""
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Ensure it starts with a letter
        if sanitized and sanitized[0].isdigit():
            sanitized = 'obj_' + sanitized
        return sanitized or 'unnamed'
    
    def generate_all(self) -> str:
        """Generate complete Terraform configuration"""
        output = []
        
        # Header
        output.append(self._generate_header())
        
        # Provider configuration
        output.append(self._generate_provider())
        
        # Address objects
        output.append(self._generate_addresses())
        
        # Address groups
        output.append(self._generate_address_groups())
        
        # Service objects
        output.append(self._generate_services())
        
        # Service groups
        output.append(self._generate_service_groups())
        
        # Zones (if using template)
        if self.template:
            output.append(self._generate_zones())
        
        # NAT pools (Dynamic IP and Port translation)
        output.append(self._generate_nat_pools())
        
        # Security policies
        output.append(self._generate_security_policies())
        
        # NAT policies
        output.append(self._generate_nat_policies())
        
        # Static routes (if using template)
        if self.template:
            output.append(self._generate_static_routes())
        
        return '\n'.join(output)
    
    def _generate_header(self) -> str:
        """Generate Terraform file header"""
        return """# FortiGate to Palo Alto Networks Terraform Configuration
# Generated automatically - Review before applying
# Provider: panos (latest version)

"""
    
    def _generate_provider(self) -> str:
        """Generate Terraform provider configuration"""
        return """terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 1.13"
    }
  }
}

provider "panos" {
  # Configure via environment variables:
  # PANOS_HOSTNAME, PANOS_USERNAME, PANOS_PASSWORD
  # Or use provider configuration
}

"""
    
    def _generate_addresses(self) -> str:
        """Generate address objects"""
        output = ["# ===== Address Objects =====\n"]
        
        for name, addr in self.parser.addresses.items():
            tf_name = self.sanitize_name(name)
            
            if addr.type == 'ipmask' and addr.subnet:
                # IP/Netmask address
                cidr_parts = addr.subnet.split('/')
                if len(cidr_parts) == 2:
                    ip, prefix = cidr_parts
                    
                    resource = f"""resource "panos_address_object" "{tf_name}" {{
  name        = "{name}"
  value       = "{addr.subnet}"
  type        = "ip-netmask"
  description = {self._format_comment(addr.comment)}
  device_group = "{self.device_group}"
}}

"""
                    output.append(resource)
            
            elif addr.type == 'iprange' and addr.ip_range:
                # IP Range
                start_ip, end_ip = addr.ip_range
                resource = f"""resource "panos_address_object" "{tf_name}" {{
  name        = "{name}"
  value       = "{start_ip}-{end_ip}"
  type        = "ip-range"
  description = {self._format_comment(addr.comment)}
  device_group = "{self.device_group}"
}}

"""
                output.append(resource)
            
            elif addr.type == 'fqdn' and addr.fqdn:
                # FQDN
                resource = f"""resource "panos_address_object" "{tf_name}" {{
  name        = "{name}"
  value       = "{addr.fqdn}"
  type        = "fqdn"
  description = {self._format_comment(addr.comment)}
  device_group = "{self.device_group}"
}}

"""
                output.append(resource)
            
            elif addr.type == 'wildcard' and addr.wildcard:
                # Wildcard (Palo Alto uses ip-wildcard type)
                resource = f"""resource "panos_address_object" "{tf_name}" {{
  name        = "{name}"
  value       = "{addr.wildcard}"
  type        = "ip-wildcard"
  description = {self._format_comment(addr.comment)}
  device_group = "{self.device_group}"
}}

"""
                output.append(resource)
        
        return ''.join(output)
    
    def _generate_address_groups(self) -> str:
        """Generate address groups"""
        output = ["# ===== Address Groups =====\n"]
        
        for name, group in self.parser.address_groups.items():
            if not group.members:
                continue
            
            tf_name = self.sanitize_name(name)
            
            # Format static members
            members_list = [f'    panos_address_object.{self.sanitize_name(m)}.name'
                           for m in group.members]
            members_str = ',\n'.join(members_list)
            depends_str = ',\n'.join(f'    panos_address_object.{self.sanitize_name(m)}' for m in group.members)

            resource = f"""resource "panos_address_group" "{tf_name}" {{
  name         = "{name}"
  description  = {self._format_comment(group.comment)}
  static_value = [
{members_str}
  ]
  device_group = "{self.device_group}"

  depends_on = [
{depends_str}
  ]
}}

"""
            output.append(resource)
        
        return ''.join(output)
    
    def _generate_services(self) -> str:
        """Generate service objects"""
        output = ["# ===== Service Objects =====\n"]
        
        for name, svc in self.parser.services.items():
            tf_name = self.sanitize_name(name)
            
            if svc.protocol in ['TCP', 'UDP']:
                # TCP/UDP service
                port_range = svc.tcp_portrange if svc.protocol == 'TCP' else svc.udp_portrange
                
                if not port_range:
                    continue
                
                # Convert FortiGate port range format to Palo Alto
                # FortiGate: "80" or "80-443" or "80:81-443:444"
                dest_ports = self._convert_port_range(port_range)
                
                resource = f"""resource "panos_service_object" "{tf_name}" {{
  name             = "{name}"
  protocol         = "{svc.protocol.lower()}"
  destination_port = "{dest_ports}"
  description      = {self._format_comment(svc.comment)}
  device_group     = "{self.device_group}"
}}

"""
                output.append(resource)
            
            elif svc.protocol in ['ICMP', 'ICMP6']:
                # ICMP service - Palo Alto doesn't have dedicated ICMP service objects
                # They use application objects or service groups
                # For simplicity, create a comment about manual migration needed
                output.append(f"# MANUAL MIGRATION REQUIRED: {name} (ICMP service)\n")
                output.append(f"# FortiGate ICMP type: {svc.icmp_type}, code: {svc.icmp_code}\n\n")
        
        return ''.join(output)
    
    def _generate_service_groups(self) -> str:
        """Generate service groups"""
        output = ["# ===== Service Groups =====\n"]
        
        for name, group in self.parser.service_groups.items():
            if not group.members:
                continue
            
            tf_name = self.sanitize_name(name)
            
            # Format members
            members_list = [f'    panos_service_object.{self.sanitize_name(m)}.name'
                           for m in group.members]
            members_str = ',\n'.join(members_list)
            depends_str = ',\n'.join(f'    panos_service_object.{self.sanitize_name(m)}' for m in group.members)

            resource = f"""resource "panos_service_group" "{tf_name}" {{
  name        = "{name}"
  services    = [
{members_str}
  ]
  device_group = "{self.device_group}"

  depends_on = [
{depends_str}
  ]
}}

"""
            output.append(resource)
        
        return ''.join(output)
    
    def _generate_zones(self) -> str:
        """Generate zone configuration"""
        output = ["# ===== Zones =====\n"]
        output.append("# Note: Review zone-to-interface mappings\n\n")
        
        # Create zones from FortiGate zones or interfaces
        zones_to_create = set()
        
        # From explicit zones
        for zone_name, members in self.parser.zones.items():
            zones_to_create.add(zone_name)
            self.zone_mapping[zone_name] = zone_name
        
        # From policies (extract unique interface names)
        for policy in self.parser.policies:
            for intf in policy.srcintf + policy.dstintf:
                if intf not in self.zone_mapping:
                    zones_to_create.add(intf)
                    self.zone_mapping[intf] = intf
        
        for zone_name in sorted(zones_to_create):
            tf_name = self.sanitize_name(zone_name)
            
            resource = f"""resource "panos_zone" "{tf_name}" {{
  name     = "{zone_name}"
  mode     = "layer3"
  template = "{self.template}"
}}

"""
            output.append(resource)
        
        return ''.join(output)
    
    def _generate_nat_pools(self) -> str:
        """Generate NAT pool configuration (as dynamic IP and port objects)"""
        output = ["# ===== NAT Pools (Dynamic IP and Port) =====\n"]
        
        for name, pool in self.parser.nat_pools.items():
            tf_name = self.sanitize_name(name)
            
            # Palo Alto uses address objects for NAT pools
            # Create address object for the pool range
            if pool.type == 'overload':
                # PAT pool - use single IP or range
                resource = f"""# NAT Pool: {name}
resource "panos_address_object" "{tf_name}_nat_pool" {{
  name        = "{name}_nat_pool"
  value       = "{pool.startip}-{pool.endip}"
  type        = "ip-range"
  description = "NAT pool from FortiGate: {pool.comments or name}"
  device_group = "{self.device_group}"
}}

"""
                output.append(resource)
        
        return ''.join(output)
    
    def _generate_security_policies(self) -> str:
        """Generate security policy rules"""
        output = ["# ===== Security Policies =====\n"]
        
        # Group policies by action
        allow_policies = [p for p in self.parser.policies if p.action == 'accept' and p.status == 'enable']
        deny_policies = [p for p in self.parser.policies if p.action == 'deny' and p.status == 'enable']
        
        # Generate allow policies
        if allow_policies:
            output.append("# Allow Policies\n")
            for policy in allow_policies:
                output.append(self._generate_security_policy(policy))
        
        # Generate deny policies
        if deny_policies:
            output.append("# Deny Policies\n")
            for policy in deny_policies:
                output.append(self._generate_security_policy(policy))
        
        return ''.join(output)
    
    def _generate_security_policy(self, policy: FirewallPolicy) -> str:
        """Generate a single security policy"""
        tf_name = self.sanitize_name(f"policy_{policy.policyid}_{policy.name}")
        
        # Map FortiGate interfaces to Palo Alto zones
        source_zones = [self.zone_mapping.get(intf, intf) for intf in policy.srcintf]
        dest_zones = [self.zone_mapping.get(intf, intf) for intf in policy.dstintf]
        
        # Handle special "all" or "any" addresses
        source_addresses = ['any'] if 'all' in policy.srcaddr else policy.srcaddr
        dest_addresses = ['any'] if 'all' in policy.dstaddr else policy.dstaddr
        
        # Handle special service names
        services = []
        for svc in policy.service:
            if svc.upper() == 'ALL':
                services = ['any']
                break
            elif svc.upper() == 'ANY':
                services = ['any']
                break
            else:
                services.append(svc)
        
        if not services:
            services = ['any']
        
        # Determine action
        action = 'allow' if policy.action == 'accept' else 'deny'
        
        # Build source addresses list
        source_addr_refs = []
        for addr in source_addresses:
            if addr != 'any':
                source_addr_refs.append(f'    panos_address_object.{self.sanitize_name(addr)}.name')
        
        source_addresses_str = '["any"]' if not source_addr_refs else '[\n' + ',\n'.join(source_addr_refs) + '\n  ]'
        
        # Build destination addresses list
        dest_addr_refs = []
        for addr in dest_addresses:
            if addr != 'any':
                dest_addr_refs.append(f'    panos_address_object.{self.sanitize_name(addr)}.name')
        
        dest_addresses_str = '["any"]' if not dest_addr_refs else '[\n' + ',\n'.join(dest_addr_refs) + '\n  ]'
        
        # Build services list
        service_refs = []
        for svc in services:
            if svc != 'any' and svc != 'application-default':
                service_refs.append(f'    panos_service_object.{self.sanitize_name(svc)}.name')
        
        if not service_refs:
            services_str = '["application-default"]'
        else:
            services_str = '[\n' + ',\n'.join(service_refs) + '\n  ]'
        
        # Build depends_on
        depends_on = []
        if self.template:
            for zone in source_zones + dest_zones:
                depends_on.append(f'    panos_zone.{self.sanitize_name(zone)}')
        
        depends_on_str = ''
        if depends_on:
            depends_items = ',\n'.join(set(depends_on))
            depends_on_str = f"""
  depends_on = [
{depends_items}
  ]"""
        
        # Logging
        log_setting = ""
        if policy.log_traffic_start == 'enable':
            log_setting = """
  log_start = true
  log_end   = true"""
        else:
            log_setting = """
  log_end   = true"""
        
        resource = f"""resource "panos_security_rule_group" "{tf_name}" {{
  position_keyword = "bottom"
  device_group     = "{self.device_group}"

  rule {{
    name                  = "{policy.name}"
    source_zones          = {json.dumps(source_zones)}
    source_addresses      = {source_addresses_str}
    destination_zones     = {json.dumps(dest_zones)}
    destination_addresses = {dest_addresses_str}
    applications          = ["any"]
    services              = {services_str}
    categories            = ["any"]
    action                = "{action}"{log_setting}
    description           = {self._format_comment(policy.comments)}
  }}{depends_on_str}
}}

"""
        return resource
    
    def _generate_nat_policies(self) -> str:
        """Generate NAT policy rules"""
        output = ["# ===== NAT Policies =====\n"]
        
        nat_policies = [p for p in self.parser.policies 
                       if p.nat == 'enable' and p.status == 'enable']
        
        for policy in nat_policies:
            output.append(self._generate_nat_policy(policy))
        
        # VIP-based destination NAT
        output.append("\n# ===== VIP-based Destination NAT =====\n")
        for name, vip in self.parser.vips.items():
            output.append(self._generate_vip_nat(name, vip))
        
        return ''.join(output)
    
    def _generate_nat_policy(self, policy: FirewallPolicy) -> str:
        """Generate a single NAT policy"""
        tf_name = self.sanitize_name(f"nat_{policy.policyid}_{policy.name}")
        
        # Map interfaces to zones
        source_zones = [self.zone_mapping.get(intf, intf) for intf in policy.srcintf]
        dest_zones = [self.zone_mapping.get(intf, intf) for intf in policy.dstintf]
        
        # Handle addresses
        source_addresses = ['any'] if 'all' in policy.srcaddr else policy.srcaddr
        dest_addresses = ['any'] if 'all' in policy.dstaddr else policy.dstaddr
        
        # Determine NAT type
        if policy.poolname:
            # Dynamic IP and Port (Source NAT with pool)
            pool_name = policy.poolname[0] if policy.poolname else None
            
            resource = f"""resource "panos_nat_rule_group" "{tf_name}" {{
  position_keyword = "bottom"
  device_group     = "{self.device_group}"

  rule {{
    name                  = "{policy.name}_nat"
    original_packet {{
      source_zones          = {json.dumps(source_zones)}
      destination_zone      = "{dest_zones[0] if dest_zones else 'any'}"
      source_addresses      = {json.dumps(source_addresses)}
      destination_addresses = {json.dumps(dest_addresses)}
    }}
    translated_packet {{
      source {{
        dynamic_ip_and_port {{
          interface_address {{
            interface = "{dest_zones[0] if dest_zones else 'ethernet1/1'}"
          }}
        }}
      }}
      destination {{}}
    }}
    description = {self._format_comment(policy.comments)}
  }}
}}

"""
        else:
            # Interface-based source NAT
            resource = f"""resource "panos_nat_rule_group" "{tf_name}" {{
  position_keyword = "bottom"
  device_group     = "{self.device_group}"

  rule {{
    name                  = "{policy.name}_nat"
    original_packet {{
      source_zones          = {json.dumps(source_zones)}
      destination_zone      = "{dest_zones[0] if dest_zones else 'any'}"
      source_addresses      = {json.dumps(source_addresses)}
      destination_addresses = {json.dumps(dest_addresses)}
    }}
    translated_packet {{
      source {{
        dynamic_ip_and_port {{
          interface_address {{
            interface = "{dest_zones[0] if dest_zones else 'ethernet1/1'}"
          }}
        }}
      }}
      destination {{}}
    }}
    description = {self._format_comment(policy.comments)}
  }}
}}

"""
        
        return resource
    
    def _generate_vip_nat(self, name: str, vip: VIP) -> str:
        """Generate NAT policy for Virtual IP (destination NAT)"""
        tf_name = self.sanitize_name(f"vip_{name}")
        
        # Determine zone
        dest_zone = self.zone_mapping.get(vip.extintf, vip.extintf) if vip.extintf != 'any' else 'any'
        
        # Port forwarding or static NAT
        if vip.portforward == 'enable' and vip.protocol and vip.extport and vip.mappedport:
            # Port forwarding (destination NAT with port translation)
            resource = f"""resource "panos_nat_rule_group" "{tf_name}" {{
  position_keyword = "bottom"
  device_group     = "{self.device_group}"

  rule {{
    name = "{name}_dnat"
    original_packet {{
      source_zones          = ["any"]
      destination_zone      = "{dest_zone}"
      destination_interface = "any"
      source_addresses      = ["any"]
      destination_addresses = ["{vip.extip}"]
      service               = "service-tcp-{vip.extport}"
    }}
    translated_packet {{
      source {{}}
      destination {{
        static_translation {{
          address = "{vip.mappedip}"
          port    = {vip.mappedport}
        }}
      }}
    }}
    description = {self._format_comment(vip.comment)}
  }}
}}

"""
        else:
            # Static NAT (1:1 NAT)
            resource = f"""resource "panos_nat_rule_group" "{tf_name}" {{
  position_keyword = "bottom"
  device_group     = "{self.device_group}"

  rule {{
    name = "{name}_static_nat"
    original_packet {{
      source_zones          = ["any"]
      destination_zone      = "{dest_zone}"
      source_addresses      = ["any"]
      destination_addresses = ["{vip.extip}"]
    }}
    translated_packet {{
      source {{}}
      destination {{
        static_translation {{
          address = "{vip.mappedip}"
        }}
      }}
    }}
    description = {self._format_comment(vip.comment)}
  }}
}}

"""
        
        return resource
    
    def _generate_static_routes(self) -> str:
        """Generate static routes"""
        if not self.template:
            return ""
        
        output = ["# ===== Static Routes =====\n"]
        output.append(f"# Note: Static routes require template configuration\n\n")
        
        # Create virtual router first (typically default)
        output.append("""resource "panos_virtual_router" "default" {
  name     = "default"
  template = \"" + self.template + "\"
}

""")
        
        for route in self.parser.static_routes:
            tf_name = self.sanitize_name(f"route_{route.seq_num}_{route.dst.replace('/', '_')}")
            
            # Parse destination
            dest = route.dst if route.dst else "0.0.0.0/0"
            
            resource = f"""resource "panos_static_route_ipv4" "{tf_name}" {{
  name           = "route_{route.seq_num}"
  virtual_router = panos_virtual_router.default.name
  destination    = "{dest}"
  interface      = "{route.device}"
  next_hop       = "{route.gateway}"
  metric         = {route.distance}
  template       = "{self.template}"
}}

"""
            output.append(resource)
        
        return ''.join(output)
    
    def _convert_port_range(self, port_range: str) -> str:
        """Convert FortiGate port range to Palo Alto format"""
        # FortiGate format: "80" or "80-443" or "80:81-443:444"
        # Palo Alto format: "80" or "80-443" or "80,81,443,444"
        
        if not port_range:
            return ""
        
        # Simple port or range
        if '-' in port_range and ':' not in port_range:
            return port_range
        
        # Single port
        if ':' not in port_range and '-' not in port_range:
            return port_range
        
        # Complex range with colons - convert to comma-separated
        # This is a simplified conversion
        parts = port_range.replace(':', ',').split('-')
        if len(parts) > 1:
            # Return first range for simplicity
            return f"{parts[0]}-{parts[1]}"
        
        return port_range
    
    def _format_comment(self, comment: Optional[str]) -> str:
        """Format comment for Terraform"""
        if comment:
            # Escape quotes and newlines
            escaped = comment.replace('"', '\\"').replace('\n', ' ')
            return f'"{escaped}"'
        return '""'


def main():
    parser = argparse.ArgumentParser(
        description='Convert FortiGate configuration to Palo Alto Terraform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using API key
  %(prog)s --host firewall.example.com --api-key YOUR_API_KEY

  # Using username/password
  %(prog)s --host firewall.example.com --username admin --password pass

  # Specify VDOM and output
  %(prog)s --host firewall.example.com --api-key KEY --vdom production -o output.tf

  # With template for zones and routes
  %(prog)s --host firewall.example.com --api-key KEY --template my-template

Environment Variables:
  FORTIGATE_HOST     - FortiGate hostname/IP
  FORTIGATE_API_KEY  - API key for authentication
  FORTIGATE_USERNAME - Username for authentication
  FORTIGATE_PASSWORD - Password for authentication
  FORTIGATE_VDOM     - VDOM to query (default: root)
        """
    )
    
    parser.add_argument('--host', 
                       default=os.environ.get('FORTIGATE_HOST'),
                       help='FortiGate hostname or IP (env: FORTIGATE_HOST)')
    
    parser.add_argument('--api-key',
                       default=os.environ.get('FORTIGATE_API_KEY'),
                       help='API key for authentication (env: FORTIGATE_API_KEY)')
    
    parser.add_argument('--username',
                       default=os.environ.get('FORTIGATE_USERNAME'),
                       help='Username for authentication (env: FORTIGATE_USERNAME)')
    
    parser.add_argument('--password',
                       default=os.environ.get('FORTIGATE_PASSWORD'),
                       help='Password for authentication (env: FORTIGATE_PASSWORD)')
    
    parser.add_argument('--vdom',
                       default=os.environ.get('FORTIGATE_VDOM', 'root'),
                       help='VDOM to query (default: root, env: FORTIGATE_VDOM)')
    
    parser.add_argument('--device-group',
                       default='shared',
                       help='Palo Alto device group (default: shared)')
    
    parser.add_argument('--vsys',
                       default='vsys1',
                       help='Palo Alto vsys (default: vsys1)')
    
    parser.add_argument('--template',
                       help='Palo Alto template name for network config')
    
    parser.add_argument('-o', '--output',
                       default='palo_alto.tf',
                       help='Output Terraform file (default: palo_alto.tf)')
    
    parser.add_argument('--verify-ssl',
                       action='store_true',
                       help='Enable SSL certificate verification (disabled by default)')
    
    parser.add_argument('--save-json',
                       help='Save raw API responses to JSON file for debugging')
    
    args = parser.parse_args()
    
    # Validation
    if not args.host:
        parser.error("FortiGate host is required (--host or FORTIGATE_HOST)")
    
    if not args.api_key and not (args.username and args.password):
        parser.error("Authentication required: --api-key or --username/--password")
    
    try:
        print(f"Connecting to FortiGate: {args.host}")
        print(f"VDOM: {args.vdom}")
        
        # Initialize API client
        api = FortiGateAPI(
            host=args.host,
            api_key=args.api_key,
            username=args.username,
            password=args.password,
            vdom=args.vdom,
            verify_ssl=args.verify_ssl
        )
        
        # Parse configuration
        fg_parser = FortiGateParser(api)
        fg_parser.parse()
        
        # Save raw JSON if requested
        if args.save_json:
            debug_data = {
                'addresses': [vars(a) for a in fg_parser.addresses.values()],
                'address_groups': [vars(g) for g in fg_parser.address_groups.values()],
                'services': [vars(s) for s in fg_parser.services.values()],
                'service_groups': [vars(g) for g in fg_parser.service_groups.values()],
                'policies': [vars(p) for p in fg_parser.policies],
                'nat_pools': [vars(p) for p in fg_parser.nat_pools.values()],
                'vips': [vars(v) for v in fg_parser.vips.values()],
                'static_routes': [vars(r) for r in fg_parser.static_routes],
                'interfaces': [vars(i) for i in fg_parser.interfaces.values()],
                'zones': fg_parser.zones
            }
            
            with open(args.save_json, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, default=str, ensure_ascii=False)
            print(f"Saved debug JSON to: {args.save_json}")
        
        # Generate Terraform
        print(f"\nGenerating Terraform configuration...")
        print(f"Device Group: {args.device_group}")
        print(f"Vsys: {args.vsys}")
        if args.template:
            print(f"Template: {args.template}")
        
        tf_gen = TerraformGenerator(
            fg_parser,
            device_group=args.device_group,
            vsys=args.vsys,
            template=args.template
        )
        
        terraform_config = tf_gen.generate_all()
        
        # Write output
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(terraform_config)
        
        print(f"\n✓ Terraform configuration written to: {args.output}")
        print(f"\nSummary:")
        print(f"  - Address Objects: {len(fg_parser.addresses)}")
        print(f"  - Address Groups: {len(fg_parser.address_groups)}")
        print(f"  - Service Objects: {len(fg_parser.services)}")
        print(f"  - Service Groups: {len(fg_parser.service_groups)}")
        print(f"  - Security Policies: {len([p for p in fg_parser.policies if p.nat == 'disable'])}")
        print(f"  - NAT Policies: {len([p for p in fg_parser.policies if p.nat == 'enable'])}")
        print(f"  - VIPs: {len(fg_parser.vips)}")
        print(f"  - Static Routes: {len(fg_parser.static_routes)}")
        print(f"  - Interfaces: {len(fg_parser.interfaces)}")
        print(f"  - Zones: {len(fg_parser.zones)}")
        
        print(f"\nNext steps:")
        print(f"  1. Review the generated Terraform file: {args.output}")
        print(f"  2. Initialize Terraform: terraform init")
        print(f"  3. Review plan: terraform plan")
        print(f"  4. Apply changes: terraform apply")
        print(f"\nNote: Manual review is recommended for:")
        print(f"  - Zone assignments and interface mappings")
        print(f"  - ICMP service objects (requires manual configuration)")
        print(f"  - Security profiles (AV, IPS, URL filtering)")
        print(f"  - Application-based policies")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    import os
    import re
    main()
