variable "project_id" {
  type    = string
  default = "ee-vivekvardhan43862"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "alert_emails" {
  type        = list(string)
  description = "Team emails that receive alert notifications"
}
