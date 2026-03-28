{{/*
Expand the name of the chart.
*/}}
{{- define "devops-info-bonus.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "devops-info-bonus.fullname" -}}
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
{{- define "devops-info-bonus.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels — delegates to the library chart.
*/}}
{{- define "devops-info-bonus.labels" -}}
{{ include "common.labels" . }}
{{- end }}

{{/*
Selector labels — delegates to the library chart.
*/}}
{{- define "devops-info-bonus.selectorLabels" -}}
{{ include "common.selectorLabels" . }}
{{- end }}
