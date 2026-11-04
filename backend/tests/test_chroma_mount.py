from unittest.mock import patch, MagicMock
import app.db.chroma as chroma
import pytest

@patch('app.db.chroma.chromadb.HttpClient')
def test_get_chroma_client_mounts_adapter(mock_http_client):
    mock_client = MagicMock()
    mock_client._server = MagicMock()
    mock_client._server._session = MagicMock()

    mock_admin_client = MagicMock()
    mock_admin_client._server = MagicMock()
    mock_admin_client._server._session = MagicMock()

    mock_client._admin_client = mock_admin_client

    mock_http_client.return_value = mock_client

    chroma._chroma_client = None
    client = chroma.get_chroma_client()

    assert mock_client._server._session.mount.call_count == 2
    assert mock_admin_client._server._session.mount.call_count == 2
