"""冒烟测试：验证 backend 骨架可运行。

这是 harness 自检的第一道门——后续所有模块测试在此基础上扩展。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "workmusic-backend"
    assert "docs" in body
