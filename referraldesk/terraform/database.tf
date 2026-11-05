resource "google_sql_database_instance" "db" {
  name             = "referraldesk-db"
  region           = "us-central1"
  database_version = "POSTGRES_16"

  settings {
    tier                        = "db-f1-micro"
    availability_type           = "ZONAL"
    disk_size                   = 10
    disk_type                   = "PD_SSD"
    enable_dataplex_integration = true

    backup_configuration {
      enabled = false
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/ee-vivekvardhan43862/global/networks/default"
      ssl_mode        = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "app" {
  name     = "referraldesk"
  instance = google_sql_database_instance.db.name
}
