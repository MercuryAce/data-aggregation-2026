"""Mongo time-series store — no-op without URI; mock when configured."""

from __future__ import annotations

from services import timeseries_store


def test_append_noop_without_uri(monkeypatch):
    monkeypatch.setattr("services.timeseries_store.Config.MONGODB_URI", "")
    timeseries_store.reset_client_for_tests()
    written = timeseries_store.append_price_ticks(
        [{"asset_id": "bitcoin", "source": "cmc", "price": 1.0}]
    )
    assert written == 0


def test_get_history_empty_without_uri(monkeypatch):
    monkeypatch.setattr("services.timeseries_store.Config.MONGODB_URI", "")
    timeseries_store.reset_client_for_tests()
    assert timeseries_store.get_price_history("bitcoin") == []


def test_append_uses_mongo_when_available(monkeypatch):
    class FakeResult:
        inserted_ids = [1, 2]

    class FakeCollection:
        def insert_many(self, docs, ordered=False):
            self.docs = docs
            return FakeResult()

        def list_collection_names(self):
            return []

    class FakeDb(dict):
        def list_collection_names(self):
            return [timeseries_store.COLLECTION]

        def __getitem__(self, key):
            return self.setdefault("_col", FakeCollection())

    fake_db = FakeDb()

    monkeypatch.setattr("services.timeseries_store.Config.MONGODB_URI", "mongodb://test")
    monkeypatch.setattr("services.timeseries_store.get_db", lambda: fake_db)
    written = timeseries_store.append_price_ticks(
        [
            {"asset_id": "bitcoin", "source": "cmc", "price": 10.0, "volume": 1},
            {"asset_id": "ethereum", "source": "cmc", "price": 2.0},
        ]
    )
    assert written == 2


def test_client_kwargs_include_tls_cert(monkeypatch, tmp_path):
    cert = tmp_path / "client.pem"
    cert.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
    monkeypatch.setattr(
        "services.timeseries_store.Config.MONGODB_TLS_CERT_FILE",
        str(cert),
    )
    kwargs = timeseries_store._client_kwargs()
    assert kwargs["tls"] is True
    assert kwargs["tlsCertificateKeyFile"] == str(cert)


def test_resolve_cert_missing_returns_none(monkeypatch):
    monkeypatch.setattr(
        "services.timeseries_store.Config.MONGODB_TLS_CERT_FILE",
        "certificates/does-not-exist.pem",
    )
    assert timeseries_store._resolve_cert_path() is None
