pipeline {
    agent none

    stages {

        stage('build') {
            agent {
                docker {
                    image 'dtzar/helm-kubectl:latest'
                    args '-u root:root'
                }
            }

            when {
                expression { return false }   // manual trigger placeholder
            }

            environment {
                KUBECONFIG = "${env.CAAS_T07_CLUSTER_KUBECONFIG}"
                REGISTRY   = "${env.REGISTRY}"
                DEVOPS_ROBOTUSER = "${env.DEVOPS_ROBOTUSER}"
                DEVOPS_TOKEN     = "${env.DEVOPS_TOKEN}"
                DEVOPS_URL       = "${env.DEVOPS_URL}"
            }

            steps {
                sh '''
                    mkdir -p .kube
                    echo "$KUBECONFIG" > .kube/config

                    docker build -f Dockerfile_logger -t $REGISTRY/k8s-event-logger .
                    docker login -u $DEVOPS_ROBOTUSER -p $DEVOPS_TOKEN $DEVOPS_URL
                    docker push $REGISTRY/k8s-event-logger
                '''
            }
        }

        stage('upgrade') {
            agent {
                docker {
                    image 'dtzar/helm-kubectl:latest'
                    args '-u root:root'
                }
            }

            // Manual approval
            input {
                message "Proceed with upgrade?"
            }

            environment {
                KUBECONFIG = "${env.CAAS_T07_CLUSTER_KUBECONFIG}"
                NAMESPACE  = "default"
                VALUES_FILE = "charts/k8s-event-logger/values.yaml"
            }

            steps {
                sh '''
                    mkdir -p /root/.kube
                    echo "$KUBECONFIG" > /root/.kube/config

                    helm delete -n $NAMESPACE event-logger || true

                    helm template event-logger ./charts/k8s-event-logger/ \
                        --values $VALUES_FILE --debug > rendered.yaml || true

                    grep -n "PersistentVolumeClaim" rendered.yaml || true

                    helm install event-logger ./charts/k8s-event-logger/ \
                        --namespace $NAMESPACE --values $VALUES_FILE

                    kubectl -n $NAMESPACE get pods | grep logger
                    kubectl -n $NAMESPACE get pvc  | grep logger

                    helm list -n $NAMESPACE
                '''
            }
        }
    }
}

