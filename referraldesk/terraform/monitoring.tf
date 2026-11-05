locals {
  ns_filter = "resource.type=\"k8s_container\" resource.labels.namespace_name=\"referraldesk\""
}

resource "google_logging_metric" "http_5xx" {
  name        = "referraldesk_http_5xx"
  description = "Backend requests that returned HTTP status 500 or higher"
  filter      = <<-EOT
    resource.type="k8s_container"
    resource.labels.namespace_name="referraldesk"
    resource.labels.container_name="backend"
    jsonPayload.event="http_request"
    jsonPayload.status_code>=500
  EOT
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_logging_metric" "http_requests" {
  name        = "referraldesk_http_requests"
  description = "All backend requests (used to compare against 5xx)"
  filter      = <<-EOT
    resource.type="k8s_container"
    resource.labels.namespace_name="referraldesk"
    resource.labels.container_name="backend"
    jsonPayload.event="http_request"
  EOT
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_monitoring_notification_channel" "email" {
  for_each     = toset(var.alert_emails)
  display_name = "ReferralDesk alerts (${each.value})"
  type         = "email"
  labels = {
    email_address = each.value
  }
}

resource "google_monitoring_alert_policy" "http_5xx" {
  display_name = "ReferralDesk: HTTP 5xx errors"
  combiner     = "OR"

  conditions {
    display_name = "More than 3 backend 5xx responses in 1 minute"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.http_5xx.name}\" AND resource.type=\"k8s_container\""
      comparison      = "COMPARISON_GT"
      threshold_value = 3
      duration        = "0s"
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [for c in google_monitoring_notification_channel.email : c.name]

  documentation {
    mime_type = "text/markdown"
    content   = "The ReferralDesk backend returned more than 3 HTTP 5xx responses within a minute. Check the JSON logs: resource.labels.namespace_name=\"referraldesk\" AND jsonPayload.status_code>=500."
  }
}

resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "ReferralDesk: Health and Errors"
    gridLayout = {
      columns = "2"
      widgets = [
        {
          title = "Requests vs HTTP 5xx errors (per minute)"
          xyChart = {
            dataSets = [
              {
                plotType       = "LINE"
                targetAxis     = "Y1"
                legendTemplate = "All requests"
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"logging.googleapis.com/user/referraldesk_http_requests\" resource.type=\"k8s_container\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              },
              {
                plotType       = "STACKED_BAR"
                targetAxis     = "Y1"
                legendTemplate = "5xx errors"
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"logging.googleapis.com/user/referraldesk_http_5xx\" resource.type=\"k8s_container\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              }
            ]
            yAxis = { label = "count", scale = "LINEAR" }
          }
        },
        {
          title = "CPU usage (cores) by container"
          xyChart = {
            dataSets = [{
              plotType   = "LINE"
              targetAxis = "Y1"
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"kubernetes.io/container/cpu/core_usage_time\" ${local.ns_filter}"
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_RATE"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["resource.labels.container_name"]
                  }
                }
              }
            }]
            yAxis = { label = "cores", scale = "LINEAR" }
          }
        },
        {
          title = "Memory used (bytes) by container"
          xyChart = {
            dataSets = [{
              plotType   = "LINE"
              targetAxis = "Y1"
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"kubernetes.io/container/memory/used_bytes\" ${local.ns_filter} metric.labels.memory_type=\"non-evictable\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_MEAN"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["resource.labels.container_name"]
                  }
                }
              }
            }]
            yAxis = { label = "bytes", scale = "LINEAR" }
          }
        },
        {
          title = "Container restarts"
          xyChart = {
            dataSets = [{
              plotType   = "STACKED_BAR"
              targetAxis = "Y1"
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"kubernetes.io/container/restart_count\" ${local.ns_filter}"
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["resource.labels.container_name"]
                  }
                }
              }
            }]
            yAxis = { label = "restarts", scale = "LINEAR" }
          }
        }
      ]
    }
  })
}
