from sqlalchemy.orm import class_mapper
from app.db.models import Message

from app.db.models import Group

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
