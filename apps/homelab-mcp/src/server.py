#!/usr/bin/env python3
"""
vGriz Homelab MCP Server
Exposes homelab infrastructure tools via Model Context Protocol over HTTP
"""

import asyncio
import json
import subprocess
from typing import Any
from aiohttp import web
import mcp.types as types

# Store tools
TOOLS = [
    {
        "name": "get_k8s_nodes",
        "description": "Get status of all Kubernetes nodes in the cluster",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_k8s_pods",
        "description": "List all pods across all namespaces with their status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Specific namespace to query (default: all namespaces)",
                }
            },
        },
    },
    {
        "name": "get_argocd_apps",
        "description": "Get status of all ArgoCD applications",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

async def run_command(cmd: list[str]) -> dict:
    """Execute a shell command and return parsed JSON output"""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        
        if proc.returncode != 0:
            return {"error": stderr.decode(), "returncode": proc.returncode}
        
        # Try to parse as JSON, otherwise return raw text
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError:
            return {"output": stdout.decode()}
    except asyncio.TimeoutError:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

async def get_k8s_nodes() -> dict:
    """Get Kubernetes node status"""
    result = await run_command(["kubectl", "get", "nodes", "-o", "json"])
    
    if "error" in result:
        return {"error": f"Error getting nodes: {result['error']}"}
    
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
    
    return {
        "summary": f"{len(nodes)} nodes total",
        "nodes": node_info,
        "details": result
    }

async def get_k8s_pods(namespace: str = "") -> dict:
    """Get Kubernetes pod status"""
    cmd = ["kubectl", "get", "pods", "-o", "json"]
    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("--all-namespaces")
    
    result = await run_command(cmd)
    
    if "error" in result:
        return {"error": f"Error getting pods: {result['error']}"}
    
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
    
    return {
        "summary": pod_summary,
        "details": result
    }

async def get_argocd_apps() -> dict:
    """Get ArgoCD application status"""
    result = await run_command([
        "kubectl", "get", "applications",
        "-n", "argocd",
        "-o", "json"
    ])
    
    if "error" in result:
        return {"error": f"Error getting ArgoCD apps: {result['error']}"}
    
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
    
    return app_summary

async def handle_tools_list(request):
    """Handle GET /tools"""
    return web.json_response({"tools": TOOLS})

async def handle_tool_call(request):
    """Handle POST /call"""
    data = await request.json()
    tool_name = data.get("name")
    arguments = data.get("arguments", {})
    
    if tool_name == "get_k8s_nodes":
        result = await get_k8s_nodes()
    elif tool_name == "get_k8s_pods":
        namespace = arguments.get("namespace", "")
        result = await get_k8s_pods(namespace)
    elif tool_name == "get_argocd_apps":
        result = await get_argocd_apps()
    else:
        return web.json_response({"error": f"Unknown tool: {tool_name}"}, status=400)
    
    return web.json_response(result)

async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy"})

def main():
    """Run the HTTP server"""
    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_get('/tools', handle_tools_list)
    app.router.add_post('/call', handle_tool_call)
    
    print("Starting homelab MCP server on port 8080...")
    web.run_app(app, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main()
