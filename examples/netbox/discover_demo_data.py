#!/usr/bin/env python3
"""
Discover what data exists in the NetBox demo database
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Add deepagents to path
sys.path.insert(0, "/home/ola/dev/rnd/deepagents/src")

from netbox_agent import get_mcp_session, call_mcp_tool, cleanup_mcp_session

async def discover_data():
    """Discover what data exists in the NetBox demo database"""

    print("=" * 80)
    print("NetBox Demo Data Discovery")
    print("=" * 80)

    try:
        # Get tenants
        print("\n1. TENANTS")
        print("-" * 80)
        tenants = await call_mcp_tool("netbox_get_objects", {
            "object_type": "tenants",
            "filters": {}
        })
        if tenants and 'results' in tenants:
            print(f"Total tenants: {len(tenants['results'])}")
            for tenant in tenants['results'][:8]:
                print(f"  - {tenant.get('name', 'N/A')} (ID: {tenant.get('id')})")

        # Get sites
        print("\n2. SITES")
        print("-" * 80)
        sites = await call_mcp_tool("netbox_get_objects", {
            "object_type": "sites",
            "filters": {}
        })
        if sites and 'results' in sites:
            print(f"Total sites: {len(sites['results'])}")
            for site in sites['results'][:10]:
                tenant = site.get('tenant', {})
                tenant_name = tenant.get('name', 'No tenant') if tenant else 'No tenant'
                print(f"  - {site.get('name', 'N/A')} ({site.get('slug', 'N/A')}) - Tenant: {tenant_name}")

        # Get device count and sample
        print("\n3. DEVICES")
        print("-" * 80)
        devices = await call_mcp_tool("netbox_get_objects", {
            "object_type": "devices",
            "filters": {}
        })
        if devices and 'results' in devices:
            print(f"Total devices: {len(devices['results'])}")
            for device in devices['results'][:10]:
                site = device.get('site', {})
                site_name = site.get('name', 'N/A') if site else 'N/A'
                device_type = device.get('device_type', {})
                model = device_type.get('model', 'N/A') if device_type else 'N/A'
                role = device.get('role', {})
                role_name = role.get('name', 'N/A') if role else 'N/A'
                print(f"  - {device.get('name', 'N/A')} ({model}) - {role_name} at {site_name}")

        # Get IP addresses
        print("\n4. IP ADDRESSES")
        print("-" * 80)
        ips = await call_mcp_tool("netbox_get_objects", {
            "object_type": "ip-addresses",
            "filters": {}
        })
        if ips and 'results' in ips:
            print(f"Total IP addresses: {len(ips['results'])}")
            for ip in ips['results'][:8]:
                assigned = ip.get('assigned_object', {})
                if assigned:
                    name = assigned.get('name', 'N/A')
                    print(f"  - {ip.get('address', 'N/A')} → {name}")
                else:
                    print(f"  - {ip.get('address', 'N/A')} (unassigned)")

        # Get VLANs
        print("\n5. VLANs")
        print("-" * 80)
        vlans = await call_mcp_tool("netbox_get_objects", {
            "object_type": "vlans",
            "filters": {}
        })
        if vlans and 'results' in vlans:
            print(f"Total VLANs: {len(vlans['results'])}")
            for vlan in vlans['results'][:8]:
                print(f"  - VLAN {vlan.get('vid', 'N/A')}: {vlan.get('name', 'N/A')}")

        # Get virtual machines
        print("\n6. VIRTUAL MACHINES")
        print("-" * 80)
        vms = await call_mcp_tool("netbox_get_objects", {
            "object_type": "virtual-machines",
            "filters": {}
        })
        if vms and 'results' in vms:
            print(f"Total VMs: {len(vms['results'])}")
            for vm in vms['results'][:8]:
                cluster = vm.get('cluster', {})
                cluster_name = cluster.get('name', 'N/A') if cluster else 'N/A'
                tenant = vm.get('tenant', {})
                tenant_name = tenant.get('name', 'No tenant') if tenant else 'No tenant'
                print(f"  - {vm.get('name', 'N/A')} on {cluster_name} (Tenant: {tenant_name})")

        # Get cables
        print("\n7. CABLES")
        print("-" * 80)
        cables = await call_mcp_tool("netbox_get_objects", {
            "object_type": "cables",
            "filters": {}
        })
        if cables and 'results' in cables:
            print(f"Total cables: {len(cables['results'])}")

        # Get racks
        print("\n8. RACKS")
        print("-" * 80)
        racks = await call_mcp_tool("netbox_get_objects", {
            "object_type": "racks",
            "filters": {}
        })
        if racks and 'results' in racks:
            print(f"Total racks: {len(racks['results'])}")
            for rack in racks['results'][:8]:
                site = rack.get('site', {})
                site_name = site.get('name', 'N/A') if site else 'N/A'
                tenant = rack.get('tenant', {})
                tenant_name = tenant.get('name', 'No tenant') if tenant else 'No tenant'
                print(f"  - {rack.get('name', 'N/A')} at {site_name} (Tenant: {tenant_name})")

        # Get prefixes
        print("\n9. IP PREFIXES")
        print("-" * 80)
        prefixes = await call_mcp_tool("netbox_get_objects", {
            "object_type": "prefixes",
            "filters": {}
        })
        if prefixes and 'results' in prefixes:
            print(f"Total prefixes: {len(prefixes['results'])}")
            for prefix in prefixes['results'][:8]:
                site = prefix.get('site', {})
                site_name = site.get('name', 'N/A') if site else 'N/A'
                vlan = prefix.get('vlan', {})
                vlan_name = vlan.get('name', 'N/A') if vlan else 'No VLAN'
                print(f"  - {prefix.get('prefix', 'N/A')} at {site_name} (VLAN: {vlan_name})")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await cleanup_mcp_session()

if __name__ == "__main__":
    asyncio.run(discover_data())
