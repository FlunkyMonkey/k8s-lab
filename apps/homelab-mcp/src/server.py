#!/usr/bin/env python3
"""
vGriz Homelab MCP Server
Exposes homelab infrastructure tools via Model Context Protocol
"""

import asyncio
import json
import subprocess
from typing import Any
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Initialize MCP server
server = Server("homelab-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available homelab tools"""
    return [
        types.Tool(
            name="get_k8s_nodes",
            description="Get status of all Kubernetes nodes in the cluster",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_k8s_pods",
            description="List all pods across all namespaces with their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Specific namespace to query (default: all namespaces)",
                    }
                },
            },
        ),
        types.Tool(
            name="get_argocd_apps",
            description="Get status of all ArgoCD applications",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_ceph_status",
            description="Get Rook-Ceph cluster health and status",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_prometheus_alerts",
            description="Get active Prometheus alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity: critical, warning, info",
                    }
                },
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    
    if name == "get_k8s_nodes":
        return await get_k8s_nodes()
    elif name == "get_k8s_pods":
        namespace = arguments.get("namespace", "") if arguments else ""
        return await get_k8s_pods(namespace)
    elif name == "get_argocd_apps":
        return await get_argocd_apps()
    elif name == "get_ceph_status":
        return await get_ceph_status()
    elif name == "get_prometheus_alerts":
        severity = arguments.get("severity", "") if arguments else ""
        return await get_prometheus_alerts(severity)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def run_command(cmd: list[str]) -> dict:
    """Execute a shell command and return parsed JSON output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return {"error": result.stderr, "returncode": result.returncode}
        
        # Try to parse as JSON, otherwise return raw text
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

async def get_k8s_nodes() -> list[types.TextContent]:
    """Get Kubernetes node status"""
    result = await run_command(["kubectl", "get", "nodes", "-o", "json"])
    
    if "error" in result:
        return [types.TextContent(
            type="text",
            text=f"Error getting nodes: {result['error']}"
        )]
    
    # Parse and format node info
    nodes = result.get("items", [])
    node_info = []
    for node in nodes:
        name = node["metadata"]["name"]
        status = "Unknown"
        for condition in node["status"]["conditions"]:
            if condition["type"] == "Ready":
                status = "Ready" if condition["status"] == "True" else "NotReady"
        
        version = node["status"]["nodeInfo"]["kubeletVersion"]
        node_info.append(f"{name}: {status} (v{version})")
    
    return [types.TextContent(
        type="text",
        text=json.dumps({
            "summary": f"{len(nodes)} nodes total",
            "nodes": node_info,
            "raw": result
        }, indent=2)
    )]

async def get_k8s_pods(namespace: str = "") -> list[types.TextContent]:
    """Get Kubernetes pod status"""
    cmd = ["kubectl", "get", "pods", "-o", "json"]
    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("--all-namespaces")
    
    result = await run_command(cmd)
    
    if "error" in result:
        return [types.TextContent(
            type="text",
            text=f"Error getting pods: {result['error']}"
        )]
    
    pods = result.get("items", [])
    pod_summary = {
        "total": len(pods),
        "running": 0,
        "pending": 0,
        "failed": 0,
        "unknown": 0
    }
    
    for pod in pods:
        phase = pod["status"].get("phase", "Unknown")
        if phase == "Running":
            pod_summary["running"] += 1
        elif phase == "Pending":
            pod_summary["pending"] += 1
        elif phase == "Failed":
            pod_summary["failed"] += 1
        else:
            pod_summary["unknown"] += 1
    
    return [types.TextContent(
        type="text",
        text=json.dumps({
            "summary": pod_summary,
            "raw": result
        }, indent=2)
    )]

async def get_argocd_apps() -> list[types.TextContent]:
    """Get ArgoCD application status"""
    result = await run_command([
        "kubectl", "get", "applications",
        "-n", "argocd",
        "-o", "json"
    ])
    
    if "error" in result:
        return [types.TextContent(
            type="text",
            text=f"Error getting ArgoCD apps: {result['error']}"
        )]
    
    apps = result.get("items", [])
    app_summary = {
        "total": len(apps),
        "synced": 0,
        "out_of_sync": 0,
        "healthy": 0,
        "degraded": 0,
        "apps": []
    }
    
    for app in apps:
        name = app["metadata"]["name"]
        sync_status = app["status"]["sync"]["status"]
        health_status = app["status"]["health"]["status"]
        
        if sync_status == "Synced":
            app_summary["synced"] += 1
        else:
            app_summary["out_of_sync"] += 1
        
        if health_status == "Healthy":
            app_summary["healthy"] += 1
        elif health_status == "Degraded":
            app_summary["degraded"] += 1
        
        app_summary["apps"].append({
            "name": name,
            "sync": sync_status,
            "health": health_status
        })
    
    return [types.TextContent(
        type="text",
        text=json.dumps(app_summary, indent=2)
    )]

async def get_ceph_status() -> list[types.TextContent]:
    """Get Rook-Ceph cluster status"""
    # Get the rook-ceph-tools pod name
    tools_pod = await run_command([
        "kubectl", "get", "pod",
        "-n", "rook-ceph",
        "-l", "app=rook-ceph-tools",
        "-o", "jsonpath={.items[0].metadata.name}"
    ])
    
    if "error" in tools_pod or not tools_pod.get("output"):
        return [types.TextContent(
            type="text",
            text="Error: Could not find rook-ceph-tools pod"
        )]
    
    pod_name = tools_pod["output"].strip()
    
    # Run ceph status
    result = await run_command([
        "kubectl", "exec", "-n", "rook-ceph", pod_name,
        "--", "ceph", "status", "-f", "json"
    ])
    
    if "error" in result:
        return [types.TextContent(
            type="text",
            text=f"Error getting Ceph status: {result['error']}"
        )]
    
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

async def get_prometheus_alerts(severity: str = "") -> list[types.TextContent]:
    """Get active Prometheus alerts"""
    # Query Prometheus API
    result = await run_command([
        "kubectl", "run", "curl-temp",
        "--rm", "-i", "--restart=Never",
        "--image=curlimages/curl:latest",
        "--", "curl", "-s",
        "http://kube-prometheus-stack-prometheus.monitoring:9090/api/v1/alerts"
    ])
    
    if "error" in result:
        return [types.TextContent(
            type="text",
            text=f"Error getting alerts: {result['error']}"
        )]
    
    # Parse the response
    try:
        alerts_data = json.loads(result.get("output", "{}"))
        alerts = alerts_data.get("data", {}).get("alerts", [])
        
        if severity:
            alerts = [a for a in alerts if a.get("labels", {}).get("severity") == severity]
        
        active_alerts = [a for a in alerts if a.get("state") == "firing"]
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "total_alerts": len(alerts),
                "active_alerts": len(active_alerts),
                "alerts": active_alerts[:10]  # Limit to 10 for brevity
            }, indent=2)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error parsing alerts: {str(e)}"
        )]

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="homelab-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
