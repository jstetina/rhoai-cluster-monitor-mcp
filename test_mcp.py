from cluster_monitor_mcp.server import mcp
import inspect

print("MCP object type:", type(mcp))
print("\nAvailable methods:")
for name in dir(mcp):
    if not name.startswith('_'):
        attr = getattr(mcp, name)
        if callable(attr):
            print(f"  - {name}{inspect.signature(attr) if hasattr(inspect, 'signature') else ''}")

print("\nLooking for app/sse related attributes:")
for name in dir(mcp):
    if 'app' in name.lower() or 'sse' in name.lower():
        print(f"  - {name}")
