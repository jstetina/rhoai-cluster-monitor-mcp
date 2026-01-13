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
        help="Transport type (stdio or http)",
        required=False,
        dest="transport",
        default="stdio",
        choices=["stdio", "http"]
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to kubeconfig file",
        required=False,
        dest="kubeconfig",
        default="/root/.kube/hive.yaml"
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
    sys.stderr.write("\n")
    
    # Set environment variables for the client
    os.environ["HIVE_KUBECONFIG"] = args.kubeconfig
    os.environ["HIVE_CONTEXT"] = args.context
    
    # Debug: Log critical environment variables
    sys.stderr.write(f"\n=== MCP Server Environment Debug ===\n")
    sys.stderr.write(f"Critical environment variables:\n")
    sys.stderr.write(f"  AWS_PROFILE: {os.environ.get('AWS_PROFILE', 'NOT SET')}\n")
    sys.stderr.write(f"  HOME: {os.environ.get('HOME', 'NOT SET')}\n")
    sys.stderr.write(f"  HIVE_KUBECONFIG: {os.environ.get('HIVE_KUBECONFIG', 'NOT SET')}\n")
    sys.stderr.write(f"  HIVE_CONTEXT: {os.environ.get('HIVE_CONTEXT', 'NOT SET')}\n")
    sys.stderr.write(f"====================================\n\n")
    sys.stderr.flush()
    
    # Run the MCP server
    try:
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        else:
            # For HTTP transport, get the ASGI app and run with uvicorn directly
            import uvicorn
            app = mcp.streamable_http_app()
            sys.stderr.write(f"Starting HTTP server on 0.0.0.0:8000\n")
            sys.stderr.flush()
            # Allow any host header for container networking
            uvicorn.run(app, host="0.0.0.0", port=8000, server_header=False, forwarded_allow_ips="*")
    except KeyboardInterrupt:
        sys.stderr.write("\n\nShutting down server...\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"\n\nError running server: {e}\n")
        import traceback
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

