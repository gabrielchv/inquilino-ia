variable "project_id" {
  description = "GCP project id"
  type        = string
  default     = "inquilino-ia"
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry"
  type        = string
  default     = "southamerica-east1"
}

variable "gemini_api_key" {
  description = "Gemini API key, injected into Secret Manager. Never commit a value for this."
  type        = string
  sensitive   = true
}

variable "supabase_db_url" {
  description = "Supabase Postgres connection string, injected into Secret Manager."
  type        = string
  sensitive   = true
}

variable "container_image" {
  description = "Fully-qualified image reference to deploy, set by CI after each build."
  type        = string
  default     = ""
}
