-- 20251009_enrich_costs.sql — Enrichissement table costs pour isolation session/user
-- Ajoute session_id et user_id pour permettre le filtrage des coûts par session

PRAGMA foreign_keys = ON;

-- Ajouter colonnes si elles n'existent pas (SQLite 3.35+)
-- Note: Pour SQLite < 3.35, cette migration devra être appliquée manuellement
ALTER TABLE costs ADD COLUMN session_id TEXT;
ALTER TABLE costs ADD COLUMN user_id TEXT;

-- Créer indexes pour optimiser les requêtes de filtrage
CREATE INDEX IF NOT EXISTS idx_costs_session
  ON costs (session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_costs_user
  ON costs (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_costs_user_session
  ON costs (user_id, session_id, timestamp DESC);

-- Vue enrichie pour faciliter les requêtes agrégées
CREATE VIEW IF NOT EXISTS v_costs_summary AS
SELECT
  user_id,
  session_id,
  agent,
  model,
  feature,
  date(timestamp) as date,
  COUNT(*) as request_count,
  SUM(input_tokens) as total_input_tokens,
  SUM(output_tokens) as total_output_tokens,
  SUM(input_tokens + output_tokens) as total_tokens,
  SUM(total_cost) as total_cost,
  AVG(total_cost) as avg_cost_per_request
FROM costs
GROUP BY user_id, session_id, agent, model, feature, date(timestamp);

-- Note: Les données existantes n'auront pas de session_id/user_id
-- Pour associer les coûts existants, il faudrait une logique métier supplémentaire
-- qui lie les timestamps de costs aux sessions actives à ce moment-là
