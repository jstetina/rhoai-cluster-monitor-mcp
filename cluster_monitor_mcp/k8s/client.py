"""Kubernetes client for Hive cluster interactions."""

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Dict, List, Optional, Any
import os
import sys


class HiveClusterClient:
    """Client for interacting with Hive cluster resources."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None, context: Optional[str] = None):
        """
        Initialize the Hive cluster client.
        
        Args:
            kubeconfig_path: Path to the kubeconfig file (defaults to env var or /home/jstetina/.kube/hive.yaml)
            context: Kubernetes context to use (defaults to env var or hive-cluster)
        """
        self.kubeconfig_path = kubeconfig_path or os.environ.get("HIVE_KUBECONFIG", "/home/jstetina/.kube/hive.yaml")
        self.context = context or os.environ.get("HIVE_CONTEXT", "hive-cluster")
        self._setup_client()
    
    def _setup_client(self):
        """Setup the Kubernetes client with the specified kubeconfig and context."""
        # Load kubeconfig
        config.load_kube_config(config_file=self.kubeconfig_path, context=self.context)
        
        # Initialize API clients
        self.core_v1 = client.CoreV1Api()
        self.custom_objects = client.CustomObjectsApi()
    
    def get_clusterclaims(self, namespace: str = "rhoai") -> List[Dict[str, Any]]:
        """
        Get all cluster claims in the specified namespace.
        
        Args:
            namespace: Namespace to search for cluster claims (default: rhoai)
            
        Returns:
            List of cluster claim objects
        """
        try:
            result = self.custom_objects.list_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=namespace,
                plural="clusterclaims"
            )
            return result.get("items", [])
        except ApiException as e:
            # Silently handle errors - likely permission issues
            return []
    
    def get_clusterdeployments(self, namespace: str) -> List[Dict[str, Any]]:
        """
        Get all cluster deployments in the specified namespace.
        
        Args:
            namespace: Namespace to search for cluster deployments
            
        Returns:
            List of cluster deployment objects
        """
        try:
            result = self.custom_objects.list_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=namespace,
                plural="clusterdeployments"
            )
            return result.get("items", [])
        except ApiException as e:
            # Silently handle errors - likely permission issues
            return []
    
    def get_all_clusterdeployments(self) -> List[Dict[str, Any]]:
        """
        Get all cluster deployments across all namespaces.
        Note: This requires cluster-wide permissions.
        
        Returns:
            List of cluster deployment objects
        """
        try:
            result = self.custom_objects.list_cluster_custom_object(
                group="hive.openshift.io",
                version="v1",
                plural="clusterdeployments"
            )
            return result.get("items", [])
        except ApiException as e:
            # If we don't have cluster-wide permissions, fall back to namespace-based approach
            return []
    
    def get_namespaces(self, label_selector: Optional[str] = None) -> List[str]:
        """
        Get all namespaces, optionally filtered by label selector.
        
        Args:
            label_selector: Label selector to filter namespaces
            
        Returns:
            List of namespace names
        """
        try:
            if label_selector:
                result = self.core_v1.list_namespace(label_selector=label_selector)
            else:
                result = self.core_v1.list_namespace()
            return [ns.metadata.name for ns in result.items]
        except ApiException as e:
            # Silently handle errors - likely permission issues
            return []
    
    def get_clusterpool(self, namespace: str, pool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific cluster pool.
        
        Args:
            namespace: Namespace containing the cluster pool
            pool_name: Name of the cluster pool
            
        Returns:
            Cluster pool object or None if not found
        """
        try:
            result = self.custom_objects.get_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=namespace,
                plural="clusterpools",
                name=pool_name
            )
            return result
        except ApiException as e:
            # Silently handle errors - likely permission issues or not found
            return None
    
    def get_clusterpools(self, namespace: str = "rhoai") -> List[Dict[str, Any]]:
        """
        Get all cluster pools in the specified namespace.
        
        Args:
            namespace: Namespace to search for cluster pools (default: rhoai)
            
        Returns:
            List of cluster pool objects
        """
        try:
            result = self.custom_objects.list_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=namespace,
                plural="clusterpools"
            )
            return result.get("items", [])
        except ApiException as e:
            # Silently handle errors - likely permission issues
            return []

