#!/bin/sh
set +x
#docker build -t k8s-event-logger -f Dockerfile_logger .
#docker run --rm -v ~/.kube:/root/.kube k8s-event-logger --config-path /root/.kube/config --namespace ecare-ta --elastic-endpoint https://your-es-endpoint --api_key "your_api_key"
whoami
pwd
ls -lah /app
ls -lah /app/data
df -h
[ ! -f /app/data/events.db ] && cp /app/events.db /app/data/
python3 /app/k8s_event_logger.py --config-path /app/.kube/config --namespace default --elastic-endpoint https://_elastic_hostname_:443 --api_key "_elastic_api_key"
