import pytest
from app.db.models import Message
from sqlalchemy import event

def test_message_has_no_orm_listeners():
    # Verify there are no ORM listeners on Message that would be bypassed.
    # Note: If `Message` relies on `before_update` or `after_update` in the future for
    # things like "updated_at" tracking, they would be intentionally bypassed here,
    # and the direct UPDATE would need to handle them manually.
    assert not event.contains(Message, 'before_update', lambda *args: None)
    assert not event.contains(Message, 'after_update', lambda *args: None)
