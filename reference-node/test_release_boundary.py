# SPDX-License-Identifier: Apache-2.0
import importlib.util
import sys
import pytest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("ori_release_server", HERE / "server.py")
server = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(HERE))
spec.loader.exec_module(server)


def test_spoofed_actor_cannot_write(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STATE_LOG", tmp_path / "events.jsonl")
    result = server.ori_challenge("anything", "ori:official:spoofed", "test", "test")
    assert result["error"] == "write_disabled"
    result = server.ori_resolve_challenge("anything", "ori:official:spoofed", "sustained", "test")
    assert result["error"] == "write_disabled"
    assert not server.STATE_LOG.exists()


def test_inventory_uses_its_schema_and_rejects_missing_fields(monkeypatch):
    path = server.ROOT / "profiles/examples/example-city/residential-new-construction-example.json"
    inventory = server._read_json(path)
    object_id = inventory["id"]
    monkeypatch.setattr(server, "_build_index", lambda: {object_id: inventory})
    result = server.ori_verify(object_id)["data"]
    assert result["schema"] == "spec/ori-jurisdiction-inventory-0.1.schema.json"
    assert result["outcome"] == "pass"
    inventory = {"id": object_id, "type": "JurisdictionInventory", "version": "0.1"}
    result = server.ori_verify(object_id)["data"]
    assert result["outcome"] == "fail"
    assert any("sources" in e["message"] for e in result["errors"])


def test_duplicate_identity_is_rejected_with_paths(monkeypatch):
    obj = {"id": "ori:duplicate", "type": "Evidence", "version": "1"}
    monkeypatch.setattr(server, "_load_documents", lambda: [(server.ROOT / "a.json", obj), (server.ROOT / "b.json", obj)])
    with pytest.raises(ValueError, match=r"duplicate_id.*a.json.*b.json"):
        server._build_index()


def test_unknown_type_is_not_promoted_to_core_pass(monkeypatch):
    monkeypatch.setattr(server, "_build_index", lambda: {"test": {"id": "test", "type": "Unknown", "version": "1"}})
    assert server.ori_verify("test")["error"] == "unsupported_type"
