resource "google_artifact_registry_repository" "images" {
  repository_id = "inquilino-ia"
  format        = "DOCKER"
  location      = var.region

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "runtime" {
  account_id   = "inquilino-ia-run"
  display_name = "InquilinoIA Cloud Run runtime identity"
}

resource "google_secret_manager_secret_iam_member" "runtime_reads_gemini_key" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_reads_supabase_url" {
  secret_id = google_secret_manager_secret.supabase_db_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_cloud_run_v2_service" "app" {
  name                = "inquilino-ia"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = var.container_image != "" ? var.container_image : "us-docker.pkg.dev/cloudrun/container/hello"

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_DB_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_db_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.runtime_reads_gemini_key,
    google_secret_manager_secret_iam_member.runtime_reads_supabase_url,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.app.name
  location = google_cloud_run_v2_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
