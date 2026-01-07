import argparse
import os
import sys
from cluster_monitor_mcp.server import mcp


def main():
    parser = argparse.ArgumentParser(
        description="RHOAI Cluster Monitor MCP Server - Monitor Hive cluster resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default)
  python main.py

  # Run with SSE transport
  python main.py --transport sse --host 0.0.0.0 --port 8080

  # Custom kubeconfig
  python main.py --kubeconfig /path/to/kubeconfig --context my-context
        """
    )
    parser.add_argument(
        "--transport",
        help="Transport type (stdio or sse)",
        required=False,
        dest="transport",
        default="stdio",
        choices=["stdio", "sse"]
    )
    parser.add_argument(
        "--host",
        help="Host to bind to (for sse transport)",
        required=False,
        dest="host",
        default="127.0.0.1"
    )
    parser.add_argument(
        "--port",
        help="Port to bind to (for sse transport)",
        required=False,
        dest="port",
        type=int,
        default=8000
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to kubeconfig file",
        required=False,
        dest="kubeconfig",
        default="/home/jstetina/.kube/hive.yaml"
    )
    parser.add_argument(
        "--context",
        help="Kubernetes context to use",
        required=False,
        dest="context",
        default="hive-cluster"
    )
    
    args = parser.parse_args()

    # Verify kubeconfig exists
    if not os.path.exists(args.kubeconfig):
        sys.stderr.write(f"Error: Kubeconfig file not found at {args.kubeconfig}\n")
        sys.stderr.write("Please provide a valid kubeconfig path using --kubeconfig\n")
        sys.exit(1)

    # Only output to stderr to avoid interfering with stdio protocol
    sys.stderr.write(f"Starting RHOAI Cluster Monitor MCP Server\n")
    sys.stderr.write(f"Kubeconfig: {args.kubeconfig}\n")
    sys.stderr.write(f"Context: {args.context}\n")
    sys.stderr.write(f"Transport: {args.transport}\n")
    
    if args.transport == "sse":
        sys.stderr.write(f"Server running at http://{args.host}:{args.port}/sse\n")
        sys.stderr.write(f"\nAvailable endpoints:\n")
        sys.stderr.write(f"  - SSE: http://{args.host}:{args.port}/sse\n")
        sys.stderr.write(f"  - Messages: http://{args.host}:{args.port}/messages\n")
        sys.stderr.write("\n")
    
    # Set environment variables for the client
    os.environ["HIVE_KUBECONFIG"] = args.kubeconfig
    os.environ["HIVE_CONTEXT"] = args.context
    
    # Run the MCP server
    try:
        if args.transport == "sse":
            mcp.run(transport="sse", host=args.host, port=args.port)
        else:
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        sys.stderr.write("\n\nShutting down server...\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"\n\nError running server: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

