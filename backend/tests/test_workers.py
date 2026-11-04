from app.db.models import Message, Group, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, load_only

def test_worker_lazy_load_deferred_columns():
    engine = create_engine('sqlite:///:memory:')
    Message.metadata.create_all(engine)
    Group.metadata.create_all(engine)
    User.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    g = Group(id="g_lazy", name="group_lazy")
    u = User(id="u_lazy", name="user_lazy")
    msg = Message(id="msg_lazy", content="test deferred loading", group_id="g_lazy", sender_id="u_lazy", is_analyzed=False, sentiment="neutral")
    session.add(g)
    session.add(u)
    session.add(msg)
    session.commit()

    from sqlalchemy import select

    # Fetch exactly like the worker task
    stmt = (
        select(Message, User)
        .outerjoin(User, Message.sender_id == User.id)
        .where(Message.id == "msg_lazy")
        .options(load_only(Message.content, Message.group_id, Message.sender_id, Message.is_analyzed))
    )
    row = session.execute(stmt).first()
    assert row is not None
    fetched_msg, fetched_user = row

    assert fetched_msg.content == "test deferred loading"
    assert fetched_user.name == "user_lazy"

    # Access a deferred column to verify lazy loading works safely without a MissingGreenlet error
    # since the worker uses sync engine, this is fully supported by the ORM contract.
    assert fetched_msg.sentiment == "neutral"
