# Terraform Configuration - Cloud SQL PostgreSQL avec pgvector
# Projet: emergence-469005
# Region: europe-west1

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "emergence-469005"
  region  = "europe-west1"
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "emergence_postgres" {
  name             = "emergence-postgres-prod"
  database_version = "POSTGRES_15"
  region           = "europe-west1"

  settings {
    tier = "db-custom-2-7680"  # 2 vCPU, 7.5GB RAM

    # Availability
    availability_type = "REGIONAL"  # HA avec failover automatique

    # Backup
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"  # 3h du matin UTC
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    # IP configuration
    ip_configuration {
      ipv4_enabled    = false  # Pas d'IP publique (sécurité)
      private_network = google_compute_network.vpc_network.id
      require_ssl     = true
    }

    # Database flags (optimisations PostgreSQL)
    database_flags {
      name  = "max_connections"
      value = "100"
    }
    database_flags {
      name  = "shared_buffers"
      value = "1966080"  # 1.875GB (25% de 7.5GB RAM)
    }
    database_flags {
      name  = "effective_cache_size"
      value = "5898240"  # 5.625GB (75% de 7.5GB RAM)
    }
    database_flags {
      name  = "maintenance_work_mem"
      value = "491520"  # 480MB
    }
    database_flags {
      name  = "checkpoint_completion_target"
      value = "0.9"
    }
    database_flags {
      name  = "wal_buffers"
      value = "16384"  # 16MB
    }
    database_flags {
      name  = "default_statistics_target"
      value = "100"
    }
    database_flags {
      name  = "random_page_cost"
      value = "1.1"  # SSD storage
    }
    database_flags {
      name  = "effective_io_concurrency"
      value = "200"  # SSD storage
    }
    database_flags {
      name  = "work_mem"
      value = "10066"  # ~10MB per connection
    }
    database_flags {
      name  = "min_wal_size"
      value = "1024"  # 1GB
    }
    database_flags {
      name  = "max_wal_size"
      value = "4096"  # 4GB
    }

    # Disk
    disk_autoresize       = true
    disk_autoresize_limit = 100  # Max 100GB
    disk_size             = 20   # Start 20GB
    disk_type             = "PD_SSD"

    # Maintenance window
    maintenance_window {
      day          = 7  # Dimanche
      hour         = 4  # 4h du matin UTC
      update_track = "stable"
    }

    # Insights config (monitoring)
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = true  # Protection contre suppression accidentelle
}

# Database principale
resource "google_sql_database" "emergence_db" {
  name     = "emergence"
  instance = google_sql_database_instance.emergence_postgres.name
}

# User application
resource "google_sql_user" "app_user" {
  name     = "emergence-app"
  instance = google_sql_database_instance.emergence_postgres.name
  password = var.db_password  # Depuis tfvars ou secret manager
}

# VPC Network (requis pour Private IP)
resource "google_compute_network" "vpc_network" {
  name                    = "emergence-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vpc_subnet" {
  name          = "emergence-subnet-europe-west1"
  ip_cidr_range = "10.0.0.0/24"
  region        = "europe-west1"
  network       = google_compute_network.vpc_network.id
}

# VPC Peering for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "emergence-cloudsql-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Outputs
output "cloudsql_connection_name" {
  value       = google_sql_database_instance.emergence_postgres.connection_name
  description = "Cloud SQL connection name for Cloud Run"
}

output "cloudsql_private_ip" {
  value       = google_sql_database_instance.emergence_postgres.private_ip_address
  description = "Private IP address of Cloud SQL instance"
}

output "database_name" {
  value = google_sql_database.emergence_db.name
}
