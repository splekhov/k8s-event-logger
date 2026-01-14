# python3 k8s_event_logger.py --config-path ~/.kube_t07/config --namespace default --elastic-endpoint https://elastic_host:443 --api_key "base64"
import argparse
import threading
import sqlite3
import yaml
import requests
from kubernetes import client, config, watch
from datetime import datetime, timedelta
import time
import os

# Shared lock for database access
db_lock = threading.Lock()

def parse_args():
    parser = argparse.ArgumentParser(description="Kubernetes Event Logger")
    parser.add_argument('--namespace', default='ecare-ta', help='Kubernetes namespace (default: default)')
    parser.add_argument('--config-path', default='~/.kube/config', help='Path to kubeconfig file (default: ~/.kube/config)')
    parser.add_argument('--elastic-endpoint', help='ElasticSearch endpoint (e.g., https://your-es.com)')
    parser.add_argument('--api_key', help='ElasticSearch API key')
    return parser.parse_args()

def get_cluster_name(config_path):
    with open(config_path, 'r') as f:
        kube_config = yaml.safe_load(f)
    current_context_name = kube_config.get('current-context')
    context = next((ctx for ctx in kube_config['contexts'] if ctx['name'] == current_context_name), None)
    cluster_name = context['context']['cluster'] if context else 'unknown-cluster'
    return cluster_name

def fetch_k8s_events(namespace, config_path, cluster_id, event_queue):
    config.load_kube_config(config_file=config_path)
    v1 = client.CoreV1Api()
    w = watch.Watch()
    print(f"Watching events in namespace: {namespace}")
    for event in w.stream(v1.list_namespaced_event, namespace=namespace):
        evt = event['object']
        event_data = {
            'reason': evt.reason or 'N/A',
            'object_kind': evt.involved_object.kind,
            'message': evt.message,
            'name': evt.involved_object.name,
            'dt': evt.last_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ') if evt.last_timestamp else 'N/A',
            #'cluster': cluster_id,
            'cluster': get_cluster_name(config_path),
            'is_loaded': 0
        }
        print(event_data)
        event_queue.append(event_data)

def db_and_elastic_worker(event_queue, elastic_endpoint=None, api_key=None):
    conn = sqlite3.connect('/app/data/events.db', check_same_thread=False)
    cursor = conn.cursor()
    headers = {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json"
    } if elastic_endpoint and api_key else None

    while True:
        # Insert new events from queue
        while event_queue:
            event = event_queue.pop(0)
            try:
                with db_lock:
                    cursor.execute('''
                        INSERT INTO kube_events (reason, object_kind, message, name, dt, cluster, is_loaded)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event['reason'],
                        event['object_kind'],
                        event['message'],
                        event['name'],
                        event['dt'],
                        event['cluster'],
                        event['is_loaded']
                    ))
                    conn.commit()
            except sqlite3.IntegrityError:
                continue

        # If ElasticSearch is configured, upload events
        if elastic_endpoint and api_key:
            with db_lock:
                cursor.execute("SELECT * FROM kube_events WHERE is_loaded=0")
                rows = cursor.fetchall()

            for row in rows:
                event_id, reason, kind, message, name, dt, cluster, is_loaded = row

                index_url = f"{elastic_endpoint.rstrip('/')}/{cluster.lower()}/_doc/{event_id}"
                index_check_url = f"{elastic_endpoint.rstrip('/')}/{cluster.lower()}"

                # Ensure index exists
                resp = requests.head(index_check_url, headers=headers)
                if resp.status_code == 404:
                    requests.put(index_check_url, headers=headers)

                # Upload event
                payload = {
                    "reason": reason,
                    "object_kind": kind,
                    "message": message,
                    "name": name,
                    "dt": dt,
                    "cluster": cluster
                }
                resp = requests.put(index_url, headers=headers, json=payload)

                if resp.status_code in (200, 201):
                    with db_lock:
                        try:
                            cursor.execute("UPDATE kube_events SET is_loaded=1 WHERE id=?", (event_id,))
                            conn.commit()
                        except sqlite3.OperationalError as e:
                            print(f"Failed to update event {event_id}: {e}")
                        continue

        # Delete old loaded events
        cutoff = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with db_lock:
            try:
                cursor.execute("DELETE FROM kube_events WHERE is_loaded=1 AND dt < ?", (cutoff,))
                conn.commit()
            except sqlite3.OperationalError as e:
                print(f"Failed to delete old events: {e}")

    time.sleep(10)

if __name__ == '__main__':
    args = parse_args()
    cluster_name = get_cluster_name(args.config_path)
    cluster_id = f"{args.namespace}:{cluster_name}"
    event_queue = []
    threading.Thread(target=fetch_k8s_events, args=(args.namespace, args.config_path, cluster_id, event_queue), daemon=True).start()
    threading.Thread(target=db_and_elastic_worker, args=(event_queue, args.elastic_endpoint, args.api_key), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
