resource "google_container_cluster" "primary" {
  name               = "referraldesk-cluster"
  location           = "us-central1-c"
  network            = "default"
  subnetwork         = "default"
  initial_node_count = 2

  release_channel {
    channel = "REGULAR"
  }

  workload_identity_config {
    workload_pool = "ee-vivekvardhan43862.svc.id.goog"
  }

  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  deletion_protection = true

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      node_config,
      node_pool,
      initial_node_count,
      node_version,
      min_master_version,
      ip_allocation_policy,
      resource_labels,
    ]
  }
}
