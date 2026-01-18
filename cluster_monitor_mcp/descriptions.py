"""Tool descriptions for MCP server."""

LIST_ALL_CLUSTERS = """List all clusters managed by the Hive cluster with optional filtering.

This tool provides a comprehensive view of all OpenShift clusters managed by Hive,
including their current state, platform, region, version, and access URLs.

The tool handles two types of clusters:
1. Regular clusters: Use clusterclaims and clusterpools (most AWS, GCP clusters)
2. IBM clusters: Directly managed without pools (special case)

Args:
    platform_filter: Filter by cloud platform (e.g., 'aws', 'gcp', 'ibmcloud', 'azure'). 
                    Case-insensitive partial match supported.
    name_filter: Filter by cluster name (partial match, case-insensitive).
                Example: 'bvt' will match all BVT clusters.
    state_filter: Filter by cluster state (e.g., 'Running', 'Hibernating', 'Resuming').
                 Case-insensitive partial match supported.
    region_filter: Filter by cloud region (e.g., 'us-east', 'us-west', 'us-south').
                  Case-insensitive partial match supported.
    owner_filter: Filter by cluster owner/provisioner (partial match, case-insensitive).
    include_details: If True, includes additional details like API URLs, console URLs,
                    infra IDs, and cluster IDs. Default is False for cleaner output.

Returns:
    A formatted string containing cluster information in a tabular format,
    including cluster name, pool, platform, region, version, state, and optionally
    detailed connection information. Returns a user-friendly message if no clusters
    match the filters.

Examples:
    - list_all_clusters(): Lists all clusters with basic information
    - list_all_clusters(platform_filter='aws'): Lists only AWS clusters
    - list_all_clusters(name_filter='bvt', state_filter='Running'): Lists running BVT clusters
    - list_all_clusters(platform_filter='ibm', include_details=True): Lists IBM clusters with full details"""

GET_CLUSTER_DETAILS = """Get detailed information about a specific cluster.

This tool provides comprehensive details about a single cluster, including all
metadata, specifications, and status information. Useful for deep-diving into
a specific cluster's configuration and current state.

Args:
    cluster_name: The exact name of the cluster to retrieve details for.
                 This should match the cluster name as shown in list_all_clusters().
                 Examples: 'afarm-pool-c7v86', 'modelsibm', 'bvt-rhoai-gcp-1-pool-fg8zt'

Returns:
    A formatted JSON string containing the complete cluster information including:
    - Basic info (name, platform, region, version, state)
    - Pool information (if applicable)
    - Network details (API URL, console URL)
    - Infrastructure details (infra ID, cluster ID)
    - Complete status and conditions
    - Full metadata and labels
    
    Returns an error message if the cluster is not found.

Examples:
    - get_cluster_details('afarm-pool-c7v86'): Get details for a specific cluster
    - get_cluster_details('modelsibm'): Get details for an IBM cluster"""

GET_CLUSTER_COUNT_BY_PLATFORM = """Get a summary count of clusters grouped by cloud platform.

This tool provides a quick overview of the cluster distribution across different
cloud providers. Useful for understanding resource allocation and identifying
which platforms are most heavily used.

Returns:
    A formatted string showing the count of clusters per platform, along with
    a breakdown by state (Running, Hibernating, etc.) for each platform.
    Also includes total cluster count.

Example output:
    Platform Statistics
    ==================
    AWS: 45 clusters
      - Running: 38
      - Hibernating: 5
      - Resuming: 2
    GCP: 23 clusters
      - Running: 20
      - Hibernating: 3
    IBM: 8 clusters
      - Running: 8
    ==================
    Total: 76 clusters"""

GET_CLUSTER_COUNT_BY_STATE = """Get a summary count of clusters grouped by their current state.

This tool provides insights into cluster health and resource utilization by
showing how many clusters are in each state (Running, Hibernating, etc.).
Useful for identifying potential issues or understanding overall cluster fleet status.

Returns:
    A formatted string showing the count of clusters in each state, along with
    a list of cluster names for each state. Also includes total cluster count.

Example output:
    State Statistics
    ==================
    Running: 65 clusters
      - afarm-pool-c7v86
      - bvt-rhoai-gcp-1-pool-fg8zt
      ...
    Hibernating: 8 clusters
      - test-cluster-1
      ...
    Resuming: 3 clusters
      - aws-nana-2-pool-hsnwc
      ...
    ==================
    Total: 76 clusters"""

GET_CLUSTER_OWNERS = """Get a list of all unique cluster owners/provisioners.

This tool returns all unique owners who have provisioned clusters, along with
the count of clusters each owner has. Useful for identifying who is using
cluster resources and how many clusters each person has provisioned.

Returns:
    A structured response with:
    - total_owners: Number of unique owners
    - owners: List of owners with their cluster counts, sorted by count descending

Example output:
    {
        "total_owners": 45,
        "owners": [
            {"name": "Scott_Froberg", "cluster_count": 5},
            {"name": "Jakub_Stetina", "cluster_count": 3},
            ...
        ]
    }"""

TEST_HIVE_CONNECTION = """Test the connection to the Hive cluster.

This tool verifies that the MCP server can successfully connect to the Hive cluster
and access its resources. Useful for troubleshooting connection issues or verifying
proper configuration.

Returns:
    A success message with basic cluster information if connection is successful,
    or an error message with details if connection fails.

Examples:
    - test_hive_connection(): Verify connectivity to Hive cluster"""

