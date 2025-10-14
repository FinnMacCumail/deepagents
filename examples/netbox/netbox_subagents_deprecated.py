"""
DEPRECATED: Sub-agent infrastructure for NetBox agent

This file preserves the original sub-agent creation code that was removed
from the main netbox_agent.py file. Sub-agents were disabled after validation
testing showed that direct sequential execution in the main agent context was
more efficient than spawning specialized domain sub-agents.

Key findings from validation (see VALIDATION_RESULTS_SUMMARY.md):
- 0 task() calls across all 5 validation queries
- Sub-agents never actually used despite being available
- Direct execution patterns proved optimal for all query types
- Sub-agent overhead unnecessary for NetBox's 3-tool MCP interface

This code is preserved for reference only and should not be used.
"""

from prompts import SUB_AGENT_PROMPT_TEMPLATE


def create_netbox_subagents():
    """Create domain-specific sub-agents for simple MCP (3 tools each)

    DEPRECATED: This function is no longer used. Sub-agents have been disabled
    in favor of direct sequential execution in the main agent context.
    """

    # All specialists use the same 3 simple MCP tools
    simple_tools = [
        "netbox_get_objects",
        "netbox_get_object_by_id",
        "netbox_get_changelogs"
    ]

    # Format sub-agent prompts with object_type guidance
    dcim_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="DCIM",
        expertise_areas="physical infrastructure management",
        detailed_expertise="""
        - Device inventory: servers, switches, routers, PDUs
        - Rack management: layouts, elevations, utilization
        - Site topology: locations, regions, hierarchies
        - Cable management: connections, paths, types
        - Power distribution: outlets, feeds, consumption
        - Physical interfaces: ports, connections, speeds

        **Your object_types**: devices, sites, racks, cables, interfaces,
        manufacturers, device-types, device-roles, platforms, power-outlets,
        power-ports, power-feeds, power-panels, modules, locations,
        console-ports, console-server-ports, front-ports, inventory-items

        **Examples**:
        - List devices: netbox_get_objects("devices", {"site": "DM-Akron"})
        - Get device: netbox_get_object_by_id("devices", 123)
        - Find racks: netbox_get_objects("racks", {"location": "Building-A"})
        - List sites: netbox_get_objects("sites", {})"""
    )

    ipam_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="IPAM",
        expertise_areas="network addressing and allocation",
        detailed_expertise="""
        - IP address management: assignments, availability, conflicts
        - Prefix allocation: subnets, utilization, hierarchies
        - VLAN configuration: IDs, names, groups, assignments
        - VRF segmentation: routing domains, isolation
        - Address resolution: DNS, DHCP reservations
        - Network services: NAT pools, anycast addresses

        **Your object_types**: ip-addresses, prefixes, vlans, vlan-groups,
        vrfs, asns, asn-ranges, aggregates, ip-ranges, services, roles,
        route-targets, rirs, fhrp-groups

        **Examples**:
        - Find IPs: netbox_get_objects("ip-addresses", {"vrf": "prod"})
        - Get prefix: netbox_get_object_by_id("prefixes", 45)
        - List VLANs: netbox_get_objects("vlans", {"site": "DM-Akron"})
        - Get VRF: netbox_get_objects("vrfs", {"name": "management"})"""
    )

    tenancy_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="Tenancy",
        expertise_areas="organizational structure and ownership",
        detailed_expertise="""
        - Tenant management: organizations, departments, customers
        - Resource ownership: device assignments, IP allocations
        - Contact information: technical, administrative, billing
        - Organizational hierarchy: parent-child relationships
        - Resource quotas: limits, allocations, usage
        - Multi-tenancy boundaries: isolation, sharing

        **Your object_types**: tenants, tenant-groups, contacts,
        contact-groups, contact-roles

        **Examples**:
        - List tenants: netbox_get_objects("tenants", {})
        - Get tenant: netbox_get_object_by_id("tenants", 7)
        - Find contacts: netbox_get_objects("contacts", {"role": "admin"})"""
    )

    virtualization_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="Virtualization",
        expertise_areas="virtual infrastructure management",
        detailed_expertise="""
        - Virtual machines: instances, configurations, states
        - Cluster management: hosts, resources, availability
        - Virtual interfaces: vNICs, configurations, attachments
        - VM-to-host mapping: placement, migration, affinity
        - Resource allocation: CPU, memory, storage
        - Virtual networking: vSwitches, port groups, overlays

        **Your object_types**: virtual-machines, clusters, cluster-groups,
        cluster-types, vm-interfaces

        **Examples**:
        - List VMs: netbox_get_objects("virtual-machines", {"cluster": "prod-cluster"})
        - Get VM: netbox_get_object_by_id("virtual-machines", 89)
        - Find clusters: netbox_get_objects("clusters", {"site": "DM-Akron"})"""
    )

    system_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="System",
        expertise_areas="system monitoring and metadata",
        detailed_expertise="""
        - Change audit logs
        - System status and diagnostics
        - Historical tracking

        **Your tools**:
        - netbox_get_changelogs: Get change audit logs with filters
        - netbox_get_objects: Access any NetBox object type

        **Examples**:
        - Recent changes: netbox_get_changelogs({"time_after": "2025-09-30T00:00:00Z"})
        - Deletions: netbox_get_changelogs({"action": "delete"})"""
    )

    return [
        {
            "name": "dcim-specialist",
            "description": "Physical infrastructure specialist. Handles devices, racks, sites, cables, and power. Returns structured DCIM data.",
            "prompt": dcim_prompt,
            "tools": simple_tools
        },
        {
            "name": "ipam-specialist",
            "description": "Network addressing specialist. Handles IPs, prefixes, VLANs, and VRFs. Returns structured IPAM data.",
            "prompt": ipam_prompt,
            "tools": simple_tools
        },
        {
            "name": "tenancy-specialist",
            "description": "Organizational structure specialist. Handles tenants, ownership, and contacts. Returns structured tenancy data.",
            "prompt": tenancy_prompt,
            "tools": simple_tools
        },
        {
            "name": "virtualization-specialist",
            "description": "Virtual infrastructure specialist. Handles VMs, clusters, and virtual interfaces. Returns structured virtualization data.",
            "prompt": virtualization_prompt,
            "tools": simple_tools
        },
        {
            "name": "system-specialist",
            "description": "System monitoring and metadata specialist. Handles changelogs and system queries.",
            "prompt": system_prompt,
            "tools": simple_tools
        }
    ]
