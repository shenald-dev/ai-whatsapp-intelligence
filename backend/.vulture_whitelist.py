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
# Add new whitelists for FastAPI endpoints and Pydantic schemas
semantic_search
ask_intelligence
export_intelligence
intelligence_stream
similarity
total_found
snippet
relevant_messages_count
get_db_session
health_check
dashboard_ui
