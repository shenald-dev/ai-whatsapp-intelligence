from sqlalchemy.orm import class_mapper
from app.db.models import Message

def test_message_indexes():
    mapper = class_mapper(Message)

    # Check that indices were correctly created on the columns
    indexed_columns = [col.name for col in mapper.columns if col.index]

    assert 'group_id' in indexed_columns, "group_id should be indexed on Message"
    assert 'sender_id' in indexed_columns, "sender_id should be indexed on Message"
    assert 'timestamp' in indexed_columns, "timestamp should be indexed on Message"
    assert 'id' in indexed_columns, "id should be indexed on Message"
