\echo '--- Enum existence ---'
SELECT t.typname AS enum_name
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
  AND t.typname IN (
    'definition_scope',
    'company_type',
    'domain_kind',
    'period_granularity',
    'domain_dimension_data_type',
    'domain_metric_data_type',
    'taxonomy_version_strategy'
  )
ORDER BY t.typname;

\echo '--- Core table existence ---'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'companies',
    'company_snapshots',
    'company_snapshot_heads',
    'taxonomy_definitions',
    'taxonomy_entities',
    'domain_definitions',
    'domain_dimensions',
    'domain_metrics',
    'domain_instances',
    'domain_instance_snapshots',
    'domain_instance_entities',
    'alembic_version'
  )
ORDER BY table_name;

\echo '--- Trigger function existence ---'
SELECT proname
FROM pg_proc
WHERE proname = 'set_updated_at';

\echo '--- Updated-at trigger count ---'
SELECT count(*) AS updated_at_trigger_count
FROM information_schema.triggers
WHERE trigger_name LIKE 'trg\_%\_updated_at';

\echo '--- Key indexes existence ---'
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'ix_company_snapshot_default_lookup',
    'ix_domain_instance_entities_data_gin',
    'ix_domain_instance_snapshots_company_snapshot'
  )
ORDER BY indexname;
