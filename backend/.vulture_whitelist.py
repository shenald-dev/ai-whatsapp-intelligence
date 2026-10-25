# .vulture_whitelist.py
import app.ai.engine
import app.api.endpoints
import app.main
import app.workers.celery_config

app.ai.engine.MessageAnalysis.lowercase_values
app.api.endpoints.get_groups
app.api.endpoints.get_group_stats
app.api.endpoints.get_recent_messages
app.main.root
app.main.ingest_message
app.workers.celery_config.enrich_message_task
