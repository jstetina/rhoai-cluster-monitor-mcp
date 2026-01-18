"""MCP Server with cluster monitoring tools."""

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from cluster_monitor_mcp.k8s.client import HiveClusterClient
from cluster_monitor_mcp import descriptions
from typing import Optional, List, Dict, Any
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


def get_all_cluster_data(client: HiveClusterClient) -> tuple:
    """
    Fetch all cluster data in minimal API calls.
    Falls back to per-namespace calls if cluster-wide access is not available.
    
    Returns:
        Tuple of (clusterclaims, deployments_by_namespace, ibm_clusters)
    """
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    
    # Try cluster-wide fetch first (fast path)
    all_deployments = client.get_all_clusterdeployments()
    
    # Build lookup map by namespace
    deployments_by_namespace: Dict[str, Dict[str, Any]] = {}
    
    if all_deployments:
        # Cluster-wide access worked - build map from results
        for dep in all_deployments:
            ns = dep.get("metadata", {}).get("namespace", "")
            if ns:
                deployments_by_namespace[ns] = dep
    else:
        # Fall back to per-namespace calls (slow but works without cluster-wide perms)
        for claim in clusterclaims:
            cluster_namespace = claim.get("spec", {}).get("namespace", "")
            if cluster_namespace and cluster_namespace not in deployments_by_namespace:
                deps = client.get_clusterdeployments(namespace=cluster_namespace)
                if deps:
                    deployments_by_namespace[cluster_namespace] = deps[0]
    
    # IBM clusters are directly in rhoai namespace
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    
    return clusterclaims, deployments_by_namespace, ibm_clusters


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
    
    # Get owner from labels
    claim_labels = clusterclaim.get("metadata", {}).get("labels", {})
    owner = claim_labels.get("owner", "")
    
    info = {
        "name": claim_name,
        "owner": owner,
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
            # Example: https://api.my-cluster.aws.example.com:6443
            # -> https://console-openshift-console.apps.my-cluster.aws.example.com
            try:
                api_domain = api_url.split("//")[1].split(":")[0]  # api.my-cluster.aws.example.com
                cluster_domain = ".".join(api_domain.split(".")[1:])  # my-cluster.aws.example.com
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
    owner_filter: Optional[str] = None,
    include_details: bool = False
) -> Dict[str, Any]:
    """Returns a structured response with cluster data."""
    client = get_hive_client()
    clusterclaims, deployments_by_namespace, ibm_clusters = get_all_cluster_data(client)
    
    all_clusters = []
    
    # Process regular clusters (with pools)
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployment = deployments_by_namespace.get(cluster_namespace)
            if deployment:
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
    
    if owner_filter:
        owner_filter_lower = owner_filter.lower()
        filtered_clusters = [c for c in filtered_clusters if owner_filter_lower in c.get("owner", "").lower()]
    
    # Sort by name
    filtered_clusters.sort(key=lambda x: x.get("name", ""))
    
    if include_details:
        return {
            "total": len(filtered_clusters),
            "clusters": filtered_clusters
        }
    else:
        # Just return list of names
        return {
            "total": len(filtered_clusters),
            "clusters": [c.get("name", "unknown") for c in filtered_clusters]
        }


@mcp.tool(description=descriptions.GET_CLUSTER_DETAILS)
def get_cluster_details(cluster_name: str) -> Dict[str, Any]:
    """Returns structured cluster details or error."""
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
                    return cluster_info
                else:
                    # Claim exists but no deployment yet
                    cluster_info = extract_cluster_info(claim, None)
                    cluster_info["claim"] = claim
                    return cluster_info
    
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
                return cluster_info
    
    # Try IBM clusters (they don't use pools/claims)
    ibm_clusters = client.get_clusterdeployments(namespace="rhoai")
    for deployment in ibm_clusters:
        ibm_name = deployment.get("metadata", {}).get("name", "")
        if ibm_name.lower() == search_name or ibm_name.lower().startswith(f"{search_name}-"):
            cluster_info = extract_ibm_cluster_info(deployment)
            cluster_info["deployment"] = deployment
            return cluster_info
    
    return {"error": f"Cluster '{cluster_name}' not found", "hint": "Try using list_all_clusters to see available clusters."}


@mcp.tool(description=descriptions.GET_CLUSTER_COUNT_BY_PLATFORM)
def get_cluster_count_by_platform() -> Dict[str, Any]:
    """Returns structured platform statistics."""
    client = get_hive_client()
    clusterclaims, deployments_by_namespace, ibm_clusters = get_all_cluster_data(client)
    
    platform_stats: Dict[str, Dict[str, int]] = {}
    
    # Process regular clusters
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployment = deployments_by_namespace.get(cluster_namespace)
            if deployment:
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
    
    # Calculate totals
    total_clusters = sum(
        sum(states.values()) for states in platform_stats.values()
    )
    
    return {
        "total": total_clusters,
        "by_platform": platform_stats
    }


@mcp.tool(description=descriptions.GET_CLUSTER_COUNT_BY_STATE)
def get_cluster_count_by_state() -> Dict[str, Any]:
    """Returns structured state statistics."""
    client = get_hive_client()
    clusterclaims, deployments_by_namespace, ibm_clusters = get_all_cluster_data(client)
    
    state_stats: Dict[str, List[str]] = {}
    
    # Process regular clusters
    for claim in clusterclaims:
        cluster_namespace = claim.get("spec", {}).get("namespace", "")
        if cluster_namespace:
            deployment = deployments_by_namespace.get(cluster_namespace)
            if deployment:
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
    
    # Sort clusters within each state
    for state in state_stats:
        state_stats[state] = sorted(state_stats[state])
    
    # Calculate totals
    total_clusters = sum(len(clusters) for clusters in state_stats.values())
    
    return {
        "total": total_clusters,
        "by_state": {
            state: {"count": len(clusters), "clusters": clusters}
            for state, clusters in state_stats.items()
        }
    }


@mcp.tool(description=descriptions.GET_CLUSTER_OWNERS)
def get_cluster_owners() -> Dict[str, Any]:
    """Returns a list of all unique cluster owners with their cluster counts."""
    client = get_hive_client()
    
    # Get all cluster claims
    clusterclaims = client.get_clusterclaims(namespace="rhoai")
    
    # Count clusters per owner
    owner_counts: Dict[str, int] = {}
    for claim in clusterclaims:
        owner = claim.get("metadata", {}).get("labels", {}).get("owner", "")
        if owner:
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
    
    # Sort by count descending, then by name
    sorted_owners = sorted(
        [{"name": name, "cluster_count": count} for name, count in owner_counts.items()],
        key=lambda x: (-x["cluster_count"], x["name"].lower())
    )
    
    return {
        "total_owners": len(sorted_owners),
        "owners": sorted_owners
    }


@mcp.tool(description=descriptions.TEST_HIVE_CONNECTION)
def test_hive_connection() -> Dict[str, Any]:
    """Returns structured connection test result."""
    try:
        client = get_hive_client()
        
        # Try to get cluster version
        clusterclaims = client.get_clusterclaims(namespace="rhoai")
        
        return {
            "success": True,
            "message": "Successfully connected to Hive cluster",
            "cluster_claims_count": len(clusterclaims)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

