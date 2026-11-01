import argparse
import sys
import json
import time
import random
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# Ensure UTF-8 output encoding if supported by environment
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def run_health(args):
    """Checks the health of all system components."""
    print("=" * 65)
    print(" [HEALTH CHECK] AI WhatsApp Intelligence System v2.0")
    print("=" * 65)

    # 1. Database Check
    try:
        from app.workers.tasks import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] Database: Connected & Responsive")
    except Exception as e:
        print(f"  [--] Database: Offline/Unreachable ({e})")

    # 2. ChromaDB Check
    try:
        from app.db.chroma import get_collection_stats
        stats = get_collection_stats()
        print(f"  [OK] ChromaDB Vector Store: {stats.get('status')} ({stats.get('total_embeddings')} embeddings)")
    except Exception as e:
        print(f"  [--] ChromaDB: Offline/Error ({e})")

    # 3. AI Engine LLM Check
    try:
        from app.ai.engine import ai_engine
        print(f"  [OK] AI Synthesis Engine: Active ({ai_engine.provider})")
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
    print("=" * 65)

    citations = res.get("citations", [])
    if citations:
        print("\nCITATIONS:")
        for c in citations:
            print(f" - [{c.get('sender_name')}]: \"{c.get('snippet')}\"")
        print()

def run_tasks(args):
    """Inspects and manages group action items from the terminal."""
    from app.workers.tasks import SessionLocal
    from app.db.models import ActionItem
    from sqlalchemy import select

    session = SessionLocal()
    group_id = args.group or "dev_core"

    # Complete task if flag provided
    if getattr(args, "complete", None):
        t = session.get(ActionItem, args.complete)
        if t:
            t.status = "done"
            t.completed_at = datetime.now(timezone.utc)
            session.commit()
            print(f" [DONE] Marked action item '{t.title}' as completed.")
        else:
            print(f" [!] Task '{args.complete}' not found.")
        session.close()
        return

    # Add task if flag provided
    if getattr(args, "add", None):
        new_task = ActionItem(
            id=str(uuid.uuid4()),
            group_id=group_id,
            title=args.add,
            assignee=getattr(args, "assignee", None) or "Unassigned",
            urgency=getattr(args, "urgency", "medium") or "medium",
            status="todo",
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_task)
        session.commit()
        print(f" [CREATED] New action item '{args.add}' for group '{group_id}'.")
        session.close()
        return

    stmt = select(ActionItem).where(ActionItem.group_id == group_id)
    if getattr(args, "status", None):
        stmt = stmt.where(ActionItem.status == args.status)
    stmt = stmt.order_by(ActionItem.created_at.desc())

    tasks = session.execute(stmt).scalars().all()
    session.close()

    print("=" * 75)
    print(f" ACTION ITEMS / KANBAN BOARD: {group_id} (Total: {len(tasks)})")
    print("=" * 75)
    if not tasks:
        print("  No action items found matching criteria.")
    else:
        print(f"{'STATUS':<12} {'URGENCY':<10} {'ASSIGNEE':<16} {'TITLE'}")
        print("-" * 75)
        for t in tasks:
            st = f"[{t.status.upper()}]"
            urg = t.urgency.upper()
            ass = (t.assignee or "Unassigned")[:14]
            title = (t.title or "")[:35]
            print(f"{st:<12} {urg:<10} {ass:<16} {title}")
    print("=" * 75)

def run_alerts(args):
    """Inspects and manages active incidents and alerts."""
    from app.workers.tasks import SessionLocal
    from app.db.models import Alert
    from sqlalchemy import select

    session = SessionLocal()
    group_id = args.group or "dev_core"

    if getattr(args, "resolve", None):
        a = session.get(Alert, args.resolve)
        if a:
            a.status = "resolved"
            a.resolved_at = datetime.now(timezone.utc)
            session.commit()
            print(f" [RESOLVED] Alert '{a.title}' marked as resolved.")
        else:
            print(f" [!] Alert '{args.resolve}' not found.")
        session.close()
        return

    stmt = select(Alert).where(Alert.group_id == group_id)
    if getattr(args, "status", None):
        stmt = stmt.where(Alert.status == args.status)
    stmt = stmt.order_by(Alert.created_at.desc())

    alerts = session.execute(stmt).scalars().all()
    session.close()

    print("=" * 75)
    print(f" INCIDENT ALERTS LOG: {group_id} (Total: {len(alerts)})")
    print("=" * 75)
    if not alerts:
        print("  No active alerts found. System operational.")
    else:
        print(f"{'SEVERITY':<12} {'STATUS':<12} {'TYPE':<16} {'TITLE'}")
        print("-" * 75)
        for a in alerts:
            sev = f"[{a.severity.upper()}]"
            st = a.status.upper()
            at = a.alert_type[:14]
            title = a.title[:32]
            print(f"{sev:<12} {st:<12} {at:<16} {title}")
    print("=" * 75)

def run_simulate(args):
    """Simulates realistic WhatsApp group messages for testing or live demonstrations."""
    count = args.count or 5
    group_id = args.group or "dev_core"
    group_name = args.group_name or "Engineering Core"
    url = args.url or "http://localhost:8000/api/v1/ingest"
    api_key = args.api_key or "default_secret_key"
    scenario = getattr(args, "scenario", "normal") or "normal"

    senders = [
        ("u_sarah", "Sarah Jenkins"),
        ("u_alex", "Alex Rivera"),
        ("u_david", "David Chen"),
        ("u_maria", "Maria Garcia")
    ]

    normal_messages = [
        "We need to finalize the API docs by Friday.",
        "Great work on the new dashboard guys, looks amazing!",
        "Are we still on track for the Q3 feature freeze?",
        "Can someone please review PR #402?",
        "I'll handle the database migration tomorrow morning.",
        "User engagement is up 15% since the new update.",
        "Let's schedule a 15-min sync to discuss the authentication flow.",
        "The new marketing assets are ready for review."
    ]

    incident_messages = [
        "CRITICAL ALERT: Production is throwing 500 error spikes on /api/v1/auth!",
        "Downtime detected on database cluster db-primary-01, checking logs immediately.",
        "URGENT: Staging is down after the last deployment merge.",
        "Server crash on worker node 4, looking into memory dump now.",
        "Security warning: potential token leaked in public repo test fixture!"
    ]

    task_messages = [
        "Todo: implement Redis connection pooling before launch.",
        "Alex Rivera to review authentication security headers by end of day.",
        "I'll handle refactoring the task queue worker tomorrow.",
        "Action item: update documentation with new environment variables.",
        "Need to finalize contract tests for external partner integration."
    ]

    if scenario == "incident":
        msg_pool = incident_messages
    elif scenario == "tasks":
        msg_pool = task_messages
    else:
        msg_pool = normal_messages

    print(f"\n[SIMULATOR] Scenario: '{scenario}' | Injecting {count} messages into group '{group_name}' ({group_id})...\n")

    for i in range(count):
        user_id, user_name = random.choice(senders)
        content = random.choice(msg_pool)

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
                print(f"  [SENT] ({i+1}/{count}): [{user_name}] {content[:48]}...")
        except urllib.error.URLError as e:
            # Fallback to direct DB injection if API server is not running
            print(f"  [NOTE] Webhook offline ({e.reason}). Ingesting directly into database...")
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
        description="AI WhatsApp Intelligence CLI & Autonomous Operations Tooling"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # health
    subparsers.add_parser("health", help="Check system, database, and vector store health")

    # tasks
    tasks_parser = subparsers.add_parser("tasks", help="Inspect and manage group action items & Kanban tasks")
    tasks_parser.add_argument("--group", type=str, default="dev_core", help="Target group ID")
    tasks_parser.add_argument("--status", type=str, default=None, choices=["todo", "in_progress", "done", "dismissed"])
    tasks_parser.add_argument("--add", type=str, default=None, help="Add a new action item title")
    tasks_parser.add_argument("--assignee", type=str, default=None, help="Assignee for the new action item")
    tasks_parser.add_argument("--urgency", type=str, default="medium", choices=["low", "medium", "high"])
    tasks_parser.add_argument("--complete", type=str, default=None, help="Task ID to mark completed")

    # alerts
    alerts_parser = subparsers.add_parser("alerts", help="Inspect and resolve active group incident alerts")
    alerts_parser.add_argument("--group", type=str, default="dev_core", help="Target group ID")
    alerts_parser.add_argument("--status", type=str, default=None, choices=["active", "acknowledged", "resolved"])
    alerts_parser.add_argument("--resolve", type=str, default=None, help="Alert ID to mark resolved")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Simulate realistic WhatsApp chats for testing/demo")
    sim_parser.add_argument("--count", type=int, default=5, help="Number of simulated messages to send")
    sim_parser.add_argument("--scenario", type=str, default="normal", choices=["normal", "incident", "tasks"])
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
    elif args.command == "tasks":
        run_tasks(args)
    elif args.command == "alerts":
        run_alerts(args)
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
