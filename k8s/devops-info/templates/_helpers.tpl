{{/*
Expand the name of the chart.
*/}}
{{- define "devops-info.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "devops-info.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "devops-info.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "devops-info.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "devops-info.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Kubernetes Secret name.
*/}}
{{- define "devops-info.secretName" -}}
{{- default (printf "%s-secret" (include "devops-info.fullname" .)) .Values.secret.name }}
{{- end }}

{{/*
ConfigMap names.
*/}}
{{- define "devops-info.configMapName" -}}
{{- printf "%s-config" (include "devops-info.fullname" .) }}
{{- end }}

{{- define "devops-info.envConfigMapName" -}}
{{- printf "%s-env" (include "devops-info.fullname" .) }}
{{- end }}

{{/*
Common static environment variables (bonus DRY template).
*/}}
{{- define "devops-info.envVars" -}}
- name: APP_NAME
  value: {{ .Values.env.APP_NAME | quote }}
- name: APP_DESCRIPTION
  value: {{ .Values.env.APP_DESCRIPTION | quote }}
- name: APP_VERSION
  value: {{ .Values.env.APP_VERSION | quote }}
- name: APP_VARIANT
  value: {{ .Values.env.APP_VARIANT | quote }}
{{- end }}

{{/*
Common labels — delegates to the library chart.
*/}}
{{- define "devops-info.labels" -}}
{{ include "common.labels" . }}
{{- end }}

{{/*
Selector labels — delegates to the library chart.
*/}}
{{- define "devops-info.selectorLabels" -}}
{{ include "common.selectorLabels" . }}
{{- end }}
