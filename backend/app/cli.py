import argparse
import sys
import os
import json
import time
import random
import uuid
from datetime import datetime, timezone, timedelta

# Ensure UTF-8 output encoding if supported by environment
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def get_db_session():
    from app.workers.tasks import SessionLocal
    return SessionLocal()

def run_health(args):
    """Checks the health of all system components."""
    print("=" * 65)
    print(" [HEALTH CHECK] AI WhatsApp Intelligence System")
    print("=" * 65)

    # 1. Database Check
    try:
        from app.workers.tasks import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] PostgreSQL: Connected & Responsive")
    except Exception as e:
        print(f"  [--] PostgreSQL: Offline/Unreachable ({e})")

    # 2. ChromaDB Check
    try:
        from app.db.chroma import get_collection_stats
        stats = get_collection_stats()
        print(f"  [OK] ChromaDB Vector Store: {stats.get('status')} ({stats.get('total_embeddings')} embeddings)")
    except Exception as e:
        print(f"  [--] ChromaDB: Offline/Error ({e})")

    # 3. AI Engine LLM Check
    try:
        from app.ai.engine import OPENROUTER_API_KEY, OPENAI_API_KEY
        provider = "OpenRouter" if OPENROUTER_API_KEY else ("OpenAI" if OPENAI_API_KEY else "Local Heuristic Synthesis Engine")
        print(f"  [OK] AI Synthesis Engine: Configured ({provider})")
    except Exception as e:
        print(f"  [--] AI Synthesis Engine Error: {e}")

    print("=" * 65)

def run_search(args):
    """Runs a semantic vector search from the terminal."""
    from app.db.chroma import search_message_embeddings
    query = args.query
    group = args.group
    limit = args.limit or 5

    where = {"group_id": group} if group else None
    print(f"\n[SEARCH] Querying vector space for: '{query}' (limit: {limit})...\n")
    results = search_message_embeddings(query_text=query, n_results=limit, where=where)

    if not results:
        print("No matching messages found in vector space.")
        return

    print(f"{'SIMILARITY':<12} {'MESSAGE ID':<20} {'CONTENT'}")
    print("-" * 75)
    for r in results:
        sim = f"{r.get('similarity', 0.0) * 100:.1f}%"
        msg_id = (r.get("message_id") or "")[:18]
        content = (r.get("content") or "")[:50]
        print(f"{sim:<12} {msg_id:<20} {content}")
    print("-" * 75)

def run_ask(args):
    """Executes a conversational RAG inquiry from the terminal."""
    from app.db.chroma import search_message_embeddings
    from app.ai.engine import ai_engine

    question = args.question
    group = args.group
    print(f"\n[ASK AI] Consulting group intelligence memory: '{question}'...\n")

    where = {"group_id": group} if group else None
    hits = search_message_embeddings(query_text=question, n_results=5, where=where)

    context = []
    for h in hits:
        meta = h.get("metadata", {})
        context.append({
            "message_id": h.get("message_id"),
            "sender_name": meta.get("sender_id", "Team Member"),
            "timestamp": "recently",
            "content": h.get("content", "")
        })

    res = ai_engine.answer_question_sync(question, context)
    print("=" * 65)
    print(f"ANSWER (Confidence: {res.get('confidence', 0.0) * 100:.0f}%):")
    print(res.get("answer"))
    print("\nCITATIONS:")
    for c in res.get("citations", []):
        print(f"  * \"{c.get('snippet')}\" (Message ID: {c.get('message_id')})")
    print("=" * 65)

def run_simulate(args):
    """Simulates realistic WhatsApp conversation streams for automated demo and testing."""
    import urllib.request
    import urllib.error

    url = args.url or "http://localhost:8000/api/v1/ingest"
    api_key = args.api_key or os.getenv("API_KEY", "default_secret_key")
    count = args.count or 5
    group_id = args.group or "dev_core"
    group_name = args.group_name or "Engineering Core"

    SIMULATED_PERSONAS = [
        ("u_alex", "Alex Rivera (Lead Architect)"),
        ("u_sarah", "Sarah Jenkins (Senior DevOps)"),
        ("u_marcus", "Marcus Vance (Backend Engineer)"),
        ("u_elena", "Elena Rostova (Product Manager)")
    ]

    SAMPLE_CHATS = [
        ("We decided to migrate the primary queue to Redis 7 to reduce lock contention.", "decision"),
        ("Can someone review PR #182 regarding the secret masking fix before noon?", "question"),
        ("I'll take ownership of the vector index scaling task by Thursday.", "task"),
        ("Heads up: database maintenance is scheduled for Sunday 2 AM UTC.", "announcement"),
        ("The new async ingestion benchmarks look fantastic, 4x latency improvement!", "discussion"),
        ("Action item: @marcus will update the Celery broker retry backoff parameters.", "task"),
        ("Are we blocking the release on the frontend dashboard styling?", "question"),
        ("Decision: approved the schema changes for the executive briefing export.", "decision")
    ]

    print(f"\n[SIMULATOR] Streaming {count} realistic WhatsApp messages into '{group_name}'...\n")

    for i in range(count):
        user_id, user_name = random.choice(SIMULATED_PERSONAS)
        content, _ = random.choice(SAMPLE_CHATS)

        payload = {
            "message_id": f"sim_{uuid.uuid4().hex[:12]}",
            "group_id": group_id,
            "group_name": group_name,
            "sender_id": user_id,
            "sender_name": user_name,
            "content": content,
            "timestamp": int(time.time()),
            "is_media": False
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
        )

        try:
            with urllib.request.urlopen(req):
                print(f"  [SENT] ({i+1}/{count}): [{user_name}] {content[:45]}...")
        except urllib.error.URLError as e:
            # Fallback to direct DB injection if API server is not running
            print(f"  [NOTE] Webhook endpoint offline ({e.reason}). Ingesting directly into database...")
            try:
                from app.workers.tasks import SessionLocal, process_message
                from app.db.models import Message, Group, User
                session = SessionLocal()
                if not session.get(Group, group_id):
                    session.add(Group(id=group_id, name=group_name))
                if not session.get(User, user_id):
                    session.add(User(id=user_id, name=user_name))
                msg_obj = Message(
                    id=payload["message_id"],
                    group_id=group_id,
                    sender_id=user_id,
                    content=content,
                    timestamp=datetime.now(timezone.utc),
                    is_media=False,
                    is_analyzed=False
                )
                session.add(msg_obj)
                session.commit()
                # Run worker inline
                process_message(payload["message_id"])
                print(f"  [SAVED & ENRICHED] {payload['message_id']}")
                session.close()
            except Exception as direct_err:
                print(f"  [ERROR] Failed direct ingestion: {direct_err}")

        if args.delay:
            time.sleep(args.delay)

    print("\n[COMPLETE] Simulation cycle finished.\n")

def run_briefing(args):
    """Generates an executive briefing from the terminal."""
    from app.workers.tasks import SessionLocal
    from app.db.models import Message, Group, User
    from app.ai.engine import ai_engine
    from sqlalchemy import select

    session = SessionLocal()
    group_id = args.group or "dev_core"
    hours = args.hours or 72

    group = session.get(Group, group_id)
    if not group:
        print(f"Group '{group_id}' not found in database.")
        session.close()
        return

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(Message, User.name.label("user_name"))
        .outerjoin(User, Message.sender_id == User.id)
        .where(Message.group_id == group_id)
        .where(Message.timestamp >= cutoff)
    )
    rows = session.execute(stmt).all()
    session.close()

    msgs = []
    for r in rows:
        m = r.Message
        msgs.append({
            "id": m.id,
            "content": m.content,
            "sender_name": r.user_name or "Team Member",
            "sentiment": m.sentiment,
            "classification": m.classification
        })

    briefing = ai_engine.generate_briefing_sync(group.name or group_id, msgs)

    print("=" * 65)
    print(f" EXECUTIVE BRIEFING: {group.name or group_id}")
    print(f" Window: Last {hours} Hours | Total Messages: {len(msgs)}")
    print("=" * 65)
    print("\n[EXECUTIVE SUMMARY]")
    print(briefing.get("executive_summary"))

    print("\n[KEY DECISIONS]")
    for d in briefing.get("key_decisions", []):
        print(f" * {d.get('decision')} (Decided by: {d.get('decider', 'Team')})")

    print("\n[ACTION ITEMS]")
    for a in briefing.get("action_items", []):
        print(f" * [{a.get('urgency', 'MED').upper()}] {a.get('task')} -> @{a.get('assignee', 'Unassigned')}")

    print("\n[SENTIMENT DISTRIBUTION]")
    print(briefing.get("sentiment_summary"))
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="AI WhatsApp Intelligence CLI & Developer Tooling"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # health
    subparsers.add_parser("health", help="Check system, database, and vector store health")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Simulate realistic WhatsApp chats for testing/demo")
    sim_parser.add_argument("--count", type=int, default=5, help="Number of simulated messages to send")
    sim_parser.add_argument("--group", type=str, default="dev_core", help="Target group ID")
    sim_parser.add_argument("--group-name", type=str, default="Engineering Core", help="Target group display name")
    sim_parser.add_argument("--url", type=str, default="http://localhost:8000/api/v1/ingest", help="Ingestion webhook URL")
    sim_parser.add_argument("--api-key", type=str, default="default_secret_key", help="API Key for authentication")
    sim_parser.add_argument("--delay", type=float, default=0.2, help="Delay in seconds between simulated messages")

    # search
    search_parser = subparsers.add_parser("search", help="Execute semantic vector search across messages")
    search_parser.add_argument("query", type=str, help="Natural language search query")
    search_parser.add_argument("--group", type=str, default=None, help="Optional group ID filter")
    search_parser.add_argument("--limit", type=int, default=5, help="Max results to display")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask conversational questions over group history via RAG")
    ask_parser.add_argument("question", type=str, help="Inquiry question")
    ask_parser.add_argument("--group", type=str, default=None, help="Optional group ID filter")

    # briefing
    briefing_parser = subparsers.add_parser("briefing", help="Generate an executive intelligence briefing")
    briefing_parser.add_argument("--group", type=str, default="dev_core", help="Target group ID")
    briefing_parser.add_argument("--hours", type=int, default=72, help="Lookback window in hours")

    args = parser.parse_args()

    if args.command == "health":
        run_health(args)
    elif args.command == "simulate":
        run_simulate(args)
    elif args.command == "search":
        run_search(args)
    elif args.command == "ask":
        run_ask(args)
    elif args.command == "briefing":
        run_briefing(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
