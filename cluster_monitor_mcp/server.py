"""MCP Server with cluster monitoring tools."""

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from cluster_monitor_mcp.k8s.client import HiveClusterClient
from cluster_monitor_mcp import descriptions
from typing import Optional, List, Dict, Any
import json
import os

# Disable DNS rebinding protection for Docker container networking
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

# Create MCP server with security settings
mcp = FastMCP('rhoai-cluster-monitor', transport_security=transport_security)

# Configure uvicorn to bind to 0.0.0.0 for container networking
os.environ.setdefault('UVICORN_HOST', '0.0.0.0')
os.environ.setdefault('UVICORN_PORT', '8000')

# Global client instance
_hive_client: Optional[HiveClusterClient] = None


def get_hive_client() -> HiveClusterClient:
    """Get or create the Hive cluster client."""
    global _hive_client
    if _hive_client is None:
        _hive_client = HiveClusterClient()
    return _hive_client


def extract_cluster_info(clusterclaim: Dict[str, Any], clusterdeployment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract relevant information from clusterclaim and clusterdeployment objects.
    
    Args:
        clusterclaim: The clusterclaim object
        clusterdeployment: The clusterdeployment object (optional)
        
    Returns:
        Dictionary with extracted cluster information
    """
    claim_name = clusterclaim.get("metadata", {}).get("name", "unknown")
    claim_spec = clusterclaim.get("spec", {})
    claim_status = clusterclaim.get("status", {})
    
    # The cluster namespace is in spec.namespace, not status.namespace
    cluster_namespace = claim_spec.get("namespace", "N/A")
    
    info = {
        "name": claim_name,
        "pool": claim_spec.get("clusterPoolName", "N/A"),
        "namespace": "rhoai",  # Claims are always in rhoai namespace
        "cluster_namespace": cluster_namespace,
        "pending": claim_status.get("conditions", [{}])[0].get("reason", "Unknown") if claim_status.get("conditions") else "Unknown",
    }
    
    if clusterdeployment:
        cd_spec = clusterdeployment.get("spec", {})
        cd_status = clusterdeployment.get("status", {})
        cd_metadata = clusterdeployment.get("metadata", {})
        
        # Extract platform and region from labels
        labels = cd_metadata.get("labels", {})
        platform = labels.get("hive.openshift.io/cluster-platform", "unknown")
        region = labels.get("hive.openshift.io/cluster-region", "unknown")
        version = labels.get("hive.openshift.io/version", "unknown")
        
        # Get power state and provision status
        power_state = cd_spec.get("powerState", "Unknown")
        
        # Try to determine actual state from conditions
        conditions = cd_status.get("conditions", [])
        state = "Unknown"
        
        # Check for specific conditions to determine state
        for condition in conditions:
            if condition.get("type") == "Hibernating" and condition.get("status") == "True":
                state = "Hibernating"
                break
            elif condition.get("type") == "Ready" and condition.get("status") == "True":
                state = "Running"
                break
            elif condition.get("type") == "ProvisionStopped" and condition.get("status") == "True":
                state = "ProvisionStopped"
                break
            elif condition.get("type") == "Resuming" and condition.get("status") == "True":
                state = "Resuming"
                break
        
        # If we couldn't determine from conditions, use power state
        if state == "Unknown":
            state = power_state
        
        # Get API URL
        api_url = cd_status.get("apiURL", "N/A")
        
        # Get console URL (derive from API URL)
        console_url = "N/A"
        if api_url != "N/A":
            # Extract cluster domain from API URL
            # Example: https://api.afarm-pool-c7v86.aws.rh-ods.com:6443
            # -> https://console-openshift-console.apps.afarm-pool-c7v86.aws.rh-ods.com
            try:
                api_domain = api_url.split("//")[1].split(":")[0]  # api.afarm-pool-c7v86.aws.rh-ods.com
                cluster_domain = ".".join(api_domain.split(".")[1:])  # afarm-pool-c7v86.aws.rh-ods.com
                console_url = f"https://console-openshift-console.apps.{cluster_domain}"
            except Exception:
                pass
        
        info.update({
            "platform": platform,
            "region": region,
            "version": version,
            "state": state,
            "power_state": power_state,
            "api_url": api_url,
            "console_url": console_url,
            "infra_id": cd_status.get("infraID", "N/A"),
            "cluster_id": cd_metadata.get("uid", "N/A"),
        })
    
    return info


def extract_ibm_cluster_info(clusterdeployment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract information from IBM cluster deployments (no pool).
    
    Args:
        clusterdeployment: The clusterdeployment object
        
    Returns:
        Dictionary with extracted cluster information
    """
    cd_metadata = clusterdeployment.get("metadata", {})
    cd_spec = clusterdeployment.get("spec", {})
    cd_status = clusterdeployment.get("status", {})
    
    cluster_name = cd_metadata.get("name", "unknown")
    labels = cd_metadata.get("labels", {})
    
    # Extract platform and region from labels or spec
    platform = labels.get("hive.openshift.io/cluster-platform")
    if not platform:
        platform = cd_spec.get("platform", {})
        if isinstance(platform, dict):
            # Get the first key (aws, ibmcloud, gcp, etc.)
            platform = list(platform.keys())[0] if platform else "unknown"
    
    region = labels.get("hive.openshift.io/cluster-region", "unknown")
    version = labels.get("hive.openshift.io/version", "unknown")
    
    # Get power state
    power_state = cd_spec.get("powerState", "Unknown")
    
    # Try to determine actual state from conditions
    conditions = cd_status.get("conditions", [])
    state = "Unknown"
    
    for condition in conditions:
        if condition.get("type") == "Hibernating" and condition.get("status") == "True":
            state = "Hibernating"
            break
        elif condition.get("type") == "Ready" and condition.get("status") == "True":
            state = "Running"
            break
        elif condition.get("type") == "ProvisionStopped" and condition.get("status") == "True":
            state = "ProvisionStopped"
            break
        elif condition.get("type") == "Resuming" and condition.get("status") == "True":
            state = "Resuming"
            break
    
    if state == "Unknown":
        state = power_state
    
    # Get API URL
    api_url = cd_status.get("apiURL", "N/A")
    
    # Get console URL
    console_url = "N/A"
    if api_url != "N/A":
        try:
            api_domain = api_url.split("//")[1].split(":")[0]
            cluster_domain = ".".join(api_domain.split(".")[1:])
            console_url = f"https://console-openshift-console.apps.{cluster_domain}"
        except Exception:
            pass
    
    return {
        "name": cluster_name,
        "pool": "N/A (IBM - no pool)",
        "namespace": cd_metadata.get("namespace", "rhoai"),
        "cluster_namespace": cd_metadata.get("namespace", "rhoai"),
        "platform": platform,
        "region": region,
        "version": version,
        "state": state,
        "power_state": power_state,
        "api_url": api_url,
        "console_url": console_url,
        "infra_id": cd_status.get("infraID", "N/A"),
        "cluster_id": cd_metadata.get("uid", "N/A"),
        "pending": "N/A (IBM)",
    }


@mcp.tool(description=descriptions.LIST_ALL_CLUSTERS)
def list_all_clusters(
    platform_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    state_filter: Optional[str] = None,
    region_filter: Optional[str] = None,
    include_details: bool = False
) -> str:
    client = get_hive_client()
    
    # Get all cluster claims from rhoai namespace
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    
    # Get IBM clusters (clusterdeployments in rhoai namespace)
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    
    all_clusters = []
    
    # Process regular clusters (with pools)
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployments = client.get_clusterdeployments(namespace=cluster_namespace)
            if deployments:
                deployment = deployments[0]  # There should be only one per namespace
                cluster_info = extract_cluster_info(claim, deployment)
                all_clusters.append(cluster_info)
            else:
                # No deployment found, include minimal info
                cluster_info = extract_cluster_info(claim, None)
                all_clusters.append(cluster_info)
    
    # Process IBM clusters (no pools)
    for deployment in ibm_clusters:
        cluster_info = extract_ibm_cluster_info(deployment)
        all_clusters.append(cluster_info)
    
    # Apply filters
    filtered_clusters = all_clusters
    
    if platform_filter:
        platform_filter_lower = platform_filter.lower()
        filtered_clusters = [c for c in filtered_clusters if platform_filter_lower in c.get("platform", "").lower()]
    
    if name_filter:
        name_filter_lower = name_filter.lower()
        filtered_clusters = [c for c in filtered_clusters if name_filter_lower in c.get("name", "").lower()]
    
    if state_filter:
        state_filter_lower = state_filter.lower()
        filtered_clusters = [c for c in filtered_clusters if state_filter_lower in c.get("state", "").lower()]
    
    if region_filter:
        region_filter_lower = region_filter.lower()
        filtered_clusters = [c for c in filtered_clusters if region_filter_lower in c.get("region", "").lower()]
    
    # Format output
    if not filtered_clusters:
        return "No clusters found matching the specified filters."
    
    # Build header
    if include_details:
        header = f"{'NAME':<30} {'PLATFORM':<10} {'REGION':<15} {'VERSION':<10} {'STATE':<20} {'API URL':<50} {'CONSOLE URL':<50}"
    else:
        header = f"{'NAME':<30} {'POOL':<25} {'PLATFORM':<10} {'REGION':<15} {'VERSION':<10} {'STATE':<20}"
    
    separator = "=" * len(header)
    
    lines = [
        f"Total clusters found: {len(filtered_clusters)}",
        separator,
        header,
        separator
    ]
    
    # Sort by name
    filtered_clusters.sort(key=lambda x: x.get("name", ""))
    
    for cluster in filtered_clusters:
        if include_details:
            line = f"{cluster.get('name', 'N/A'):<30} {cluster.get('platform', 'N/A'):<10} {cluster.get('region', 'N/A'):<15} {cluster.get('version', 'N/A'):<10} {cluster.get('state', 'N/A'):<20} {cluster.get('api_url', 'N/A'):<50} {cluster.get('console_url', 'N/A'):<50}"
        else:
            line = f"{cluster.get('name', 'N/A'):<30} {cluster.get('pool', 'N/A'):<25} {cluster.get('platform', 'N/A'):<10} {cluster.get('region', 'N/A'):<15} {cluster.get('version', 'N/A'):<10} {cluster.get('state', 'N/A'):<20}"
        lines.append(line)
    
    lines.append(separator)
    
    return "\n".join(lines)


@mcp.tool(description=descriptions.GET_CLUSTER_DETAILS)
def get_cluster_details(cluster_name: str) -> str:
    client = get_hive_client()
    
    # Normalize the search name
    search_name = cluster_name.lower().strip()
    
    # First, try to find it in cluster claims
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    
    for claim in clusterclaims:
        claim_name = claim.get("metadata", {}).get("name", "")
        claim_name_lower = claim_name.lower()
        
        # Match exact name, with -claim suffix, or base name
        if (claim_name_lower == search_name or 
            claim_name_lower == f"{search_name}-claim" or
            claim_name_lower.startswith(f"{search_name}-")):
            
            cluster_namespace = claim.get("spec", {}).get("namespace", "")
            if cluster_namespace:
                deployments = client.get_clusterdeployments(namespace=cluster_namespace)
                if deployments:
                    deployment = deployments[0]
                    cluster_info = extract_cluster_info(claim, deployment)
                    cluster_info["claim"] = claim
                    cluster_info["deployment"] = deployment
                    return json.dumps(cluster_info, indent=2)
                else:
                    # Claim exists but no deployment yet
                    cluster_info = extract_cluster_info(claim, None)
                    cluster_info["claim"] = claim
                    return json.dumps(cluster_info, indent=2)
    
    # Check if it's a cluster namespace name (with random suffix)
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace.lower() == search_name or cluster_namespace.lower().startswith(f"{search_name}-"):
            deployments = client.get_clusterdeployments(namespace=cluster_namespace)
            if deployments:
                deployment = deployments[0]
                cluster_info = extract_cluster_info(claim, deployment)
                cluster_info["claim"] = claim
                cluster_info["deployment"] = deployment
                return json.dumps(cluster_info, indent=2)
    
    # Try IBM clusters (they don't use pools/claims)
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    for deployment in ibm_clusters:
        ibm_name = deployment.get("metadata", {}).get("name", "")
        if ibm_name.lower() == search_name or ibm_name.lower().startswith(f"{search_name}-"):
            cluster_info = extract_ibm_cluster_info(deployment)
            cluster_info["deployment"] = deployment
            return json.dumps(cluster_info, indent=2)
    
    return f"Cluster '{cluster_name}' not found. Try using list_all_clusters to see available clusters."


@mcp.tool(description=descriptions.GET_CLUSTER_COUNT_BY_PLATFORM)
def get_cluster_count_by_platform() -> str:
    client = get_hive_client()
    
    # Get all clusters
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    
    platform_stats: Dict[str, Dict[str, int]] = {}
    
    # Process regular clusters
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployments = client.get_clusterdeployments(namespace=cluster_namespace)
            if deployments:
                deployment = deployments[0]
                cluster_info = extract_cluster_info(claim, deployment)
                
                platform = cluster_info.get("platform", "unknown")
                state = cluster_info.get("state", "Unknown")
                
                if platform not in platform_stats:
                    platform_stats[platform] = {}
                
                if state not in platform_stats[platform]:
                    platform_stats[platform][state] = 0
                
                platform_stats[platform][state] += 1
    
    # Process IBM clusters
    for deployment in ibm_clusters:
        cluster_info = extract_ibm_cluster_info(deployment)
        platform = cluster_info.get("platform", "unknown")
        state = cluster_info.get("state", "Unknown")
        
        if platform not in platform_stats:
            platform_stats[platform] = {}
        
        if state not in platform_stats[platform]:
            platform_stats[platform][state] = 0
        
        platform_stats[platform][state] += 1
    
    # Format output
    lines = [
        "Platform Statistics",
        "=" * 50
    ]
    
    total_clusters = 0
    for platform in sorted(platform_stats.keys()):
        states = platform_stats[platform]
        platform_total = sum(states.values())
        total_clusters += platform_total
        
        lines.append(f"{platform.upper()}: {platform_total} clusters")
        for state in sorted(states.keys()):
            lines.append(f"  - {state}: {states[state]}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append(f"Total: {total_clusters} clusters")
    
    return "\n".join(lines)


@mcp.tool(description=descriptions.GET_CLUSTER_COUNT_BY_STATE)
def get_cluster_count_by_state() -> str:
    client = get_hive_client()
    
    # Get all clusters
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    
    state_stats: Dict[str, List[str]] = {}
    
    # Process regular clusters
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployments = client.get_clusterdeployments(namespace=cluster_namespace)
            if deployments:
                deployment = deployments[0]
                cluster_info = extract_cluster_info(claim, deployment)
                
                state = cluster_info.get("state", "Unknown")
                name = cluster_info.get("name", "unknown")
                
                if state not in state_stats:
                    state_stats[state] = []
                
                state_stats[state].append(name)
    
    # Process IBM clusters
    for deployment in ibm_clusters:
        cluster_info = extract_ibm_cluster_info(deployment)
        state = cluster_info.get("state", "Unknown")
        name = cluster_info.get("name", "unknown")
        
        if state not in state_stats:
            state_stats[state] = []
        
        state_stats[state].append(name)
    
    # Format output
    lines = [
        "State Statistics",
        "=" * 50
    ]
    
    total_clusters = 0
    for state in sorted(state_stats.keys()):
        clusters = sorted(state_stats[state])
        state_total = len(clusters)
        total_clusters += state_total
        
        lines.append(f"{state}: {state_total} clusters")
        for cluster_name in clusters[:10]:  # Show first 10
            lines.append(f"  - {cluster_name}")
        if len(clusters) > 10:
            lines.append(f"  ... and {len(clusters) - 10} more")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append(f"Total: {total_clusters} clusters")
    
    return "\n".join(lines)


@mcp.tool(description=descriptions.TEST_HIVE_CONNECTION)
def test_hive_connection() -> str:
    try:
        client = get_hive_client()
        
        # Try to get cluster version
        clusterclaims = client.get_clusterclaims(namespace="rhoai")
        
        return f"✓ Successfully connected to Hive cluster\n✓ Found {len(clusterclaims)} cluster claims in rhoai namespace"
    except Exception as e:
        return f"✗ Failed to connect to Hive cluster: {str(e)}"

