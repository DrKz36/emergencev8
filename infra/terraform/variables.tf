# Variables Terraform pour infrastructure ÉMERGENCE

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "emergence-469005"
}

variable "region" {
  description = "GCP Region principale"
  type        = string
  default     = "europe-west1"
}

variable "db_password" {
  description = "Mot de passe PostgreSQL pour emergence-app user (depuis Secret Manager)"
  type        = string
  sensitive   = true
}

variable "redis_memory_size_gb" {
  description = "Taille mémoire Redis en GB"
  type        = number
  default     = 1
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
  default     = "prod"
}
