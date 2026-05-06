import pytest
from app.api.schemas import GroupResponse, MessageResponse

def test_group_response_construct_tuple_order():
    # Verify that model_construct aligns with the DB query column order
    # Query: select(models.Group.id, models.Group.name)
    row = ("grp_123", "Group 123")
    obj = GroupResponse.model_construct(id=row[0], name=row[1])
    assert obj.id == "grp_123"
    assert obj.name == "Group 123"

def test_message_response_construct_tuple_order():
    # Verify that model_construct aligns with the DB query column order
    # Query: select(models.Message.id, models.Message.content, models.Message.sentiment, models.Message.classification)
    row = ("msg_123", "Hello World", "positive", "discussion")
    obj = MessageResponse.model_construct(id=row[0], content=row[1], sentiment=row[2], classification=row[3])
    assert obj.id == "msg_123"
    assert obj.content == "Hello World"
    assert obj.sentiment == "positive"
    assert obj.classification == "discussion"
