from sqlalchemy.orm import class_mapper, sessionmaker, load_only
from sqlalchemy import create_engine
from app.db.models import Message

from app.db.models import Group
from app.db.database import Base

def test_message_indexes():
    mapper = class_mapper(Message)

    # Check that indices were correctly created on the columns
    indexed_columns = [col.name for col in mapper.columns if col.index]

    assert 'sender_id' in indexed_columns, "sender_id should be indexed on Message"

    assert 'group_id' not in indexed_columns, "group_id should NOT be individually indexed as it's part of a composite index"
    assert 'timestamp' not in indexed_columns, "timestamp should NOT be individually indexed as it's part of a composite index"
    assert 'id' not in indexed_columns, "id should NOT be individually indexed as it's a primary key"

def test_group_indexes():
    mapper = class_mapper(Group)
    indexed_columns = [col.name for col in mapper.columns if col.index]
    assert 'created_at' in indexed_columns, "created_at should be indexed on Group"

def test_load_only_lazy_load():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    msg = Message(id="1", group_id="g1", sender_id="s1", content="hello", is_analyzed=False, is_media=True)
    session.add(msg)
    session.commit()

    fetched_msg = session.get(
        Message,
        "1",
        options=[load_only(Message.content, Message.group_id, Message.sender_id, Message.is_analyzed)]
    )

    assert fetched_msg.content == "hello"
    assert fetched_msg.is_media is True
