{{- define "k8s-event-logger.labels" -}}
app.kubernetes.io/name: {{ include "k8s-event-logger.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "k8s-event-logger.name" -}}
{{ default .Chart.Name .Values.nameOverride }}
{{- end }}

{{- define "k8s-event-logger.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- trim .Values.fullnameOverride }}
{{- else }}
{{- printf "%s-%s" (trim (include "k8s-event-logger.name" .)) (trim .Release.Name) }}
{{- end }}
{{- end }}