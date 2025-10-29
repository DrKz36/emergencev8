# Terraform Configuration - Pub/Sub Topics & Subscriptions
# Projet: emergence-469005
# Pour orchestration agents asynchrones (Anima, Neo, Nexus)

# Topic Anima (agent Anthropic Claude)
resource "google_pubsub_topic" "agent_anima" {
  name = "agent-anima-tasks"

  labels = {
    agent       = "anima"
    environment = var.environment
  }

  # Message retention (7 jours)
  message_retention_duration = "604800s"
}

# Subscription Anima Worker
resource "google_pubsub_subscription" "anima_worker" {
  name  = "anima-worker-sub"
  topic = google_pubsub_topic.agent_anima.id

  # Ack deadline (temps pour traiter message)
  ack_deadline_seconds = 600  # 10 minutes (LLM calls peuvent être longs)

  # Message retention (7 jours)
  message_retention_duration = "604800s"

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Dead letter queue (après 5 échecs)
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  # Push config vers Cloud Run Worker
  push_config {
    push_endpoint = "https://anima-worker-${random_id.suffix.hex}-ew.a.run.app/process"

    oidc_token {
      service_account_email = google_service_account.worker_anima.email
    }

    attributes = {
      x-goog-version = "v1"
    }
  }
}

# Topic Neo (agent Google Gemini)
resource "google_pubsub_topic" "agent_neo" {
  name = "agent-neo-tasks"

  labels = {
    agent       = "neo"
    environment = var.environment
  }

  message_retention_duration = "604800s"
}

resource "google_pubsub_subscription" "neo_worker" {
  name  = "neo-worker-sub"
  topic = google_pubsub_topic.agent_neo.id

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "https://neo-worker-${random_id.suffix.hex}-ew.a.run.app/process"

    oidc_token {
      service_account_email = google_service_account.worker_neo.email
    }
  }
}

# Topic Nexus (agent OpenAI GPT)
resource "google_pubsub_topic" "agent_nexus" {
  name = "agent-nexus-tasks"

  labels = {
    agent       = "nexus"
    environment = var.environment
  }

  message_retention_duration = "604800s"
}

resource "google_pubsub_subscription" "nexus_worker" {
  name  = "nexus-worker-sub"
  topic = google_pubsub_topic.agent_nexus.id

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "https://nexus-worker-${random_id.suffix.hex}-ew.a.run.app/process"

    oidc_token {
      service_account_email = google_service_account.worker_nexus.email
    }
  }
}

# Dead Letter Queue (messages échoués)
resource "google_pubsub_topic" "dlq" {
  name = "agent-tasks-dlq"

  labels = {
    type        = "dead-letter-queue"
    environment = var.environment
  }

  message_retention_duration = "2592000s"  # 30 jours
}

resource "google_pubsub_subscription" "dlq_sub" {
  name  = "agent-tasks-dlq-sub"
  topic = google_pubsub_topic.dlq.id

  ack_deadline_seconds       = 60
  message_retention_duration = "2592000s"

  # Pas de retry sur DLQ (logging uniquement)
}

# Service Accounts pour Workers
resource "google_service_account" "worker_anima" {
  account_id   = "anima-worker"
  display_name = "Anima Worker Service Account"
}

resource "google_service_account" "worker_neo" {
  account_id   = "neo-worker"
  display_name = "Neo Worker Service Account"
}

resource "google_service_account" "worker_nexus" {
  account_id   = "nexus-worker"
  display_name = "Nexus Worker Service Account"
}

# IAM: Permissions Cloud SQL pour workers
resource "google_project_iam_member" "worker_anima_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker_anima.email}"
}

resource "google_project_iam_member" "worker_neo_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker_neo.email}"
}

resource "google_project_iam_member" "worker_nexus_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker_nexus.email}"
}

# IAM: Permissions Secret Manager pour workers (API keys)
resource "google_project_iam_member" "worker_anima_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker_anima.email}"
}

resource "google_project_iam_member" "worker_neo_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker_neo.email}"
}

resource "google_project_iam_member" "worker_nexus_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker_nexus.email}"
}

# Random suffix pour URLs uniques
resource "random_id" "suffix" {
  byte_length = 4
}

# Outputs
output "pubsub_topics" {
  value = {
    anima = google_pubsub_topic.agent_anima.id
    neo   = google_pubsub_topic.agent_neo.id
    nexus = google_pubsub_topic.agent_nexus.id
    dlq   = google_pubsub_topic.dlq.id
  }
}

output "worker_service_accounts" {
  value = {
    anima = google_service_account.worker_anima.email
    neo   = google_service_account.worker_neo.email
    nexus = google_service_account.worker_nexus.email
  }
}
