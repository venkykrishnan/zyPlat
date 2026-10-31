"""CLI tests: help text, argument checks, and client calls with a fake API."""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from zyplat_cli.client import ZyPlatClient
from zyplat_cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class FakeClient:
    """Stand-in for ``ZyPlatClient`` so the CLI can be tested without a server."""

    last: FakeClient | None = None

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.created: list[tuple[str, dict[str, Any]]] = []
        FakeClient.last = self

    def create_company(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(("company", data))
        return {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": data["name"]}

    def list_companies(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "company_id": "CO-1",
                "name": "First",
                "company_type": "LENDER",
            }
        ]

    def create_taxonomy_definition(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(("taxonomy", data))
        return {"id": "11111111-1111-1111-1111-111111111111", "taxonomy_id": data["taxonomy_id"]}

    def create_taxonomy_entity(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(("entity", data))
        return data

    def list_taxonomy_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "taxonomy_id": "accountType",
                "version": "1.0.0",
                "scope_type": "GLOBAL",
                "is_hierarchical": True,
            }
        ]

    def create_domain_definition(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(("domain", data))
        return {"id": "22222222-2222-2222-2222-222222222222", "domain_id": data["domain_id"]}

    def list_domain_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "domain_id": "GL",
                "kind": "TIME_SERIES",
                "scope_type": "GLOBAL",
            }
        ]


@pytest.fixture
def fake_client(monkeypatch) -> type[FakeClient]:
    monkeypatch.setattr("zyplat_cli.main.ZyPlatClient", FakeClient)
    FakeClient.last = None
    return FakeClient


class TestHelp:
    """Users find commands from the help text."""

    @pytest.mark.parametrize(
        "args",
        [[], ["company"], ["taxonomy"], ["domain"], ["company", "create"]],
    )
    def test_help_exits_zero(self, runner, args):
        """Every group and the create command must document themselves."""
        result = runner.invoke(cli, [*args, "--help"])

        assert result.exit_code == 0


class TestCompanyCommands:
    def test_create_without_args_is_a_usage_error(self, runner, fake_client):
        """Create needs either a file or the id/name/type trio."""
        result = runner.invoke(cli, ["company", "create"])

        assert result.exit_code != 0
        assert "Either --file or" in result.output

    def test_create_from_flags_sends_the_company(self, runner, fake_client):
        """Flag input must reach the API client."""
        result = runner.invoke(
            cli,
            ["company", "create", "--company-id", "CO-1", "--name", "First", "--type", "LENDER"],
        )

        assert result.exit_code == 0
        assert FakeClient.last is not None
        assert FakeClient.last.created[0][1]["company_id"] == "CO-1"

    def test_create_from_file_sends_the_json(self, runner, fake_client, tmp_path):
        """A JSON file is the bulk-import path."""
        path = tmp_path / "co.json"
        path.write_text(
            json.dumps({"company_id": "CO-2", "name": "Second", "company_type": "LENDER"})
        )

        result = runner.invoke(cli, ["company", "create", "--file", str(path)])

        assert result.exit_code == 0
        assert FakeClient.last is not None
        assert FakeClient.last.created[0][1]["company_id"] == "CO-2"

    def test_list_prints_company_rows(self, runner, fake_client):
        """List must show the fields operators look for."""
        result = runner.invoke(cli, ["company", "list"])

        assert result.exit_code == 0
        assert "CO-1" in result.output
        assert "First" in result.output

    def test_list_aborts_when_the_api_fails(self, runner, monkeypatch):
        """A down API must not look like an empty list."""

        class Down(FakeClient):
            def list_companies(self):
                raise ConnectionError("refused")

        monkeypatch.setattr("zyplat_cli.main.ZyPlatClient", Down)

        result = runner.invoke(cli, ["company", "list"])

        assert result.exit_code != 0
        assert "refused" in result.output


class TestTaxonomyAndDomainCommands:
    def test_taxonomy_list_prints_rows(self, runner, fake_client):
        result = runner.invoke(cli, ["taxonomy", "list"])

        assert result.exit_code == 0
        assert "accountType" in result.output

    def test_domain_list_prints_rows(self, runner, fake_client):
        result = runner.invoke(cli, ["domain", "list"])

        assert result.exit_code == 0
        assert "GL" in result.output

    def test_taxonomy_create_from_file_creates_entities(self, runner, fake_client, tmp_path):
        """Legacy input files include nested entities that must be posted too."""
        path = tmp_path / "tax.json"
        path.write_text(
            json.dumps(
                {
                    "id": "accountType",
                    "description": "Accounts",
                    "isHierarchical": True,
                    "entities": [{"id": "asset", "value": "Asset", "displayName": "Asset"}],
                }
            )
        )

        result = runner.invoke(cli, ["taxonomy", "create", "--file", str(path)])

        assert result.exit_code == 0
        kinds = [kind for kind, _ in FakeClient.last.created]  # type: ignore[union-attr]
        assert kinds == ["taxonomy", "entity"]

    def test_domain_create_from_file(self, runner, fake_client, tmp_path):
        path = tmp_path / "gl.json"
        path.write_text(json.dumps({"id": "GL", "description": "Ledger", "isTimeSeries": True}))

        result = runner.invoke(cli, ["domain", "create", "--file", str(path)])

        assert result.exit_code == 0
        assert FakeClient.last is not None
        assert FakeClient.last.created[0][1]["kind"] == "TIME_SERIES"


class TestZyPlatClient:
    """The HTTP client maps methods onto the REST paths the API exposes."""

    @staticmethod
    def _client(monkeypatch, payload: Any, status: int = 200) -> ZyPlatClient:
        captured: dict[str, Any] = {}

        class FakeResponse:
            def raise_for_status(self) -> None:
                if status >= 400:
                    raise RuntimeError(f"HTTP {status}")

            def json(self) -> Any:
                return payload

        def fake_request(self, method, url, **kwargs):
            captured.update(method=method, url=url, kwargs=kwargs)
            return FakeResponse()

        monkeypatch.setattr("zyplat_cli.client.requests.Session.request", fake_request)
        client = ZyPlatClient("http://example.test/api/v1")
        client.captured = captured  # type: ignore[attr-defined]
        return client

    def test_create_company_posts_json(self, monkeypatch):
        client = self._client(monkeypatch, {"id": "1"})

        result = client.create_company({"name": "A"})

        assert result == {"id": "1"}
        assert client.captured["method"] == "POST"  # type: ignore[attr-defined]
        assert client.captured["url"].endswith("/companies")  # type: ignore[attr-defined]

    def test_list_companies_gets_a_list(self, monkeypatch):
        client = self._client(monkeypatch, [{"id": "1"}])

        assert client.list_companies() == [{"id": "1"}]

    def test_get_update_and_delete_company(self, monkeypatch):
        client = self._client(monkeypatch, {"id": "1"})

        client.get_company("1")
        client.update_company("1", {"name": "B"})
        client.delete_company("1")

        assert client.captured["method"] == "DELETE"  # type: ignore[attr-defined]

    def test_taxonomy_and_domain_paths(self, monkeypatch):
        client = self._client(monkeypatch, {"id": "1"})

        client.create_taxonomy_definition({"taxonomy_id": "t"})
        client.list_taxonomy_definitions()
        client.get_taxonomy_definition("t")
        client.create_taxonomy_entity({"entity_id": "e"})
        client.list_taxonomy_entities("t")
        client.create_domain_definition({"domain_id": "d"})
        client.list_domain_definitions()
        client.get_domain_definition("d")

        assert client.captured["url"].endswith("/domains/d")  # type: ignore[attr-defined]

    def test_import_from_file_dispatches_by_type(self, monkeypatch, tmp_path):
        path = tmp_path / "item.json"
        path.write_text(json.dumps({"name": "A"}))
        client = self._client(monkeypatch, {"id": "1"})

        assert client.import_from_file(str(path), "company") == {"id": "1"}
        with pytest.raises(ValueError, match="Unknown entity type"):
            client.import_from_file(str(path), "snapshot")
