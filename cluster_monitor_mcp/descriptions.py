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
                 Owner names are stored in format "Firstname_Surname" (underscore separator).
                 You can search by partial name - e.g., "john" will match "John_Smith".
                 Use this to find clusters belonging to a specific person.
    include_details: If True, includes additional details like API URLs, console URLs,
                    infra IDs, and cluster IDs. Default is False for cleaner output.

Returns:
    A formatted string containing cluster information in a tabular format,
    including cluster name, pool, platform, region, version, state, and optionally
    detailed connection information. Returns a user-friendly message if no clusters
    match the filters.

IMPORTANT - Finding clusters by owner:
    When asked about a specific person's clusters:
    1. If you know the full name, use owner_filter with "Firstname_Surname" format
       Example: owner_filter="John_Smith"
    2. If you only know partial name (first or last), use owner_filter with just that part
       Example: owner_filter="smith" will find all owners with "smith" in their name
    3. If no clusters are found or you need to verify the exact owner name format,
       use get_cluster_owners() first to see all available owner names

Examples:
    - list_all_clusters(): Lists all clusters with basic information
    - list_all_clusters(platform_filter='aws'): Lists only AWS clusters
    - list_all_clusters(name_filter='bvt', state_filter='Running'): Lists running BVT clusters
    - list_all_clusters(owner_filter='John_Smith'): Lists clusters owned by John Smith
    - list_all_clusters(owner_filter='john'): Lists clusters where owner contains "john"
    - list_all_clusters(platform_filter='ibm', include_details=True): Lists IBM clusters with full details"""

GET_CLUSTER_DETAILS = """Get detailed information about a specific cluster.

This tool provides comprehensive details about a single cluster, including all
metadata, specifications, and status information. Useful for deep-diving into
a specific cluster's configuration and current state.

Args:
    cluster_name: The exact name of the cluster to retrieve details for.
                 This should match the cluster name as shown in list_all_clusters().

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
    - get_cluster_details('my-cluster-claim'): Get details for a specific cluster
    - get_cluster_details('dev-ibm-cluster'): Get details for an IBM cluster"""

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
      - prod-aws-cluster-1
      - dev-gcp-cluster-2
      ...
    Hibernating: 8 clusters
      - staging-cluster-1
      ...
    Resuming: 3 clusters
      - test-cluster-1
      ...
    ==================
    Total: 76 clusters"""

GET_CLUSTER_OWNERS = """Get a list of all unique cluster owners/provisioners.

This tool returns all unique owners who have provisioned clusters, along with
the count of clusters each owner has. Useful for identifying who is using
cluster resources and how many clusters each person has provisioned.

IMPORTANT - Owner name format:
    Owner names are stored as "Firstname_Surname" (underscore separator).
    Examples: "John_Smith", "Jane_Doe", "Alice_Johnson"

When to use this tool:
    1. When you need to see all available cluster owners
    2. When you're unsure of the exact owner name format
    3. Before using list_all_clusters(owner_filter=...) if you don't know the exact name
    4. When asked "who owns clusters" or "list cluster owners"

Workflow for finding a specific owner's clusters:
    1. If you don't know the exact owner name format, call get_cluster_owners() first
    2. Find the matching owner name (format: Firstname_Surname)
    3. Then call list_all_clusters(owner_filter="Firstname_Surname") to get their clusters

Returns:
    A structured response with:
    - total_owners: Number of unique owners
    - owners: List of owners with their cluster counts, sorted by count descending
    
    Each owner entry contains:
    - name: Owner name in "Firstname_Surname" format
    - cluster_count: Number of clusters owned by this person"""

TEST_HIVE_CONNECTION = """Test the connection to the Hive cluster.

This tool verifies that the MCP server can successfully connect to the Hive cluster
and access its resources. Useful for troubleshooting connection issues or verifying
proper configuration.

Returns:
    A success message with basic cluster information if connection is successful,
    or an error message with details if connection fails.

Examples:
    - test_hive_connection(): Verify connectivity to Hive cluster"""
