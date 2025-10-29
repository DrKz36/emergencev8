# Terraform Configuration - Memorystore Redis
# Projet: emergence-469005
# Region: europe-west1

# Memorystore Redis Instance (HA)
resource "google_redis_instance" "emergence_redis" {
  name               = "emergence-redis-prod"
  tier               = "STANDARD_HA"  # HA avec failover automatique
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  redis_version      = "REDIS_7_0"
  display_name       = "ÉMERGENCE Production Redis Cache"

  # Configuration réseau (même VPC que Cloud SQL)
  authorized_network = google_compute_network.vpc_network.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  # Maintenance window
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 4
        minutes = 0
      }
    }
  }

  # Redis configuration
  redis_configs = {
    maxmemory-policy = "allkeys-lru"  # Eviction LRU automatique
    notify-keyspace-events = "Ex"     # Notifications expiration
    timeout = "300"                    # Connection timeout 5min
  }

  # Labels pour organisation
  labels = {
    environment = var.environment
    application = "emergence"
    managed_by  = "terraform"
  }
}

# Output Redis connection
output "redis_host" {
  value       = google_redis_instance.emergence_redis.host
  description = "Redis host IP address"
}

output "redis_port" {
  value       = google_redis_instance.emergence_redis.port
  description = "Redis port"
}

output "redis_connection_string" {
  value       = "redis://${google_redis_instance.emergence_redis.host}:${google_redis_instance.emergence_redis.port}"
  description = "Redis connection string for application"
  sensitive   = true
}
