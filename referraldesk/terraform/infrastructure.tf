resource "google_service_account" "app" {
  account_id   = "referraldesk-vm-sa"
  display_name = "ReferralDesk VM service account"
}

resource "google_storage_bucket" "uploads" {
  name                        = "ee-vivekvardhan43862-referraldesk-uploads"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket_iam_member" "app_object_user" {
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.app.email}"
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "referraldesk-db-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "app_secret_access" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

resource "google_artifact_registry_repository" "repo" {
  location      = "us-central1"
  repository_id = "referraldesk-repo"
  format        = "DOCKER"

  cleanup_policy_dry_run = true

  docker_config {
    immutable_tags = false
  }
}

resource "google_artifact_registry_repository_iam_member" "app_registry_reader" {
  location   = google_artifact_registry_repository.repo.location
  repository = google_artifact_registry_repository.repo.repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.app.email}"
}

resource "google_compute_global_address" "ingress_ip" {
  name = "referraldesk-ip"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:ee-vivekvardhan43862.svc.id.goog[referraldesk/referraldesk-app]"
}
