#!/usr/bin/env python3

import sys
import re
from kubernetes import client, config

def main():
    if len(sys.argv) != 3:
        print("Usage: ./pod_alerter.py <pattern> <namespace>")
        sys.exit(1)

    pattern = sys.argv[1]
    namespace = sys.argv[2]

    try:
        # Load kubeconfig from ~/.kube/config
        config.load_kube_config()
    except Exception as e:
        print(f"Failed to load kubeconfig: {e}")
        sys.exit(1)

    v1 = client.CoreV1Api()

    try:
        pods = v1.list_namespaced_pod(namespace)
    except client.exceptions.ApiException as e:
        print(f"Failed to list pods in namespace '{namespace}': {e}")
        sys.exit(1)

    print(f"Pods matching pattern '{pattern}' in namespace '{namespace}':")
    matched = False
    for pod in pods.items:
        if re.search(pattern, pod.metadata.name):
            print(f"- {pod.metadata.name}")
            matched = True

    if not matched:
        print("No matching pods found.")

if __name__ == "__main__":
    main()

