import json
from typing import Any

import requests


class ZyPlatClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _object(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Send a request and return the JSON object the API responds with."""
        body: dict[str, Any] = self._request(method, path, **kwargs).json()
        return body

    def _list(self, method: str, path: str, **kwargs) -> list[dict[str, Any]]:
        """Send a request and return the JSON list the API responds with."""
        body: list[dict[str, Any]] = self._request(method, path, **kwargs).json()
        return body

    # Company operations
    def create_company(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._object("POST", "/companies", json=data)

    def list_companies(self) -> list[dict[str, Any]]:
        return self._list("GET", "/companies")

    def get_company(self, company_id: str) -> dict[str, Any]:
        return self._object("GET", f"/companies/{company_id}")

    def update_company(self, company_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._object("PUT", f"/companies/{company_id}", json=data)

    def delete_company(self, company_id: str) -> None:
        self._request("DELETE", f"/companies/{company_id}")

    # Taxonomy operations
    def create_taxonomy_definition(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._object("POST", "/taxonomies/definitions", json=data)

    def list_taxonomy_definitions(self) -> list[dict[str, Any]]:
        return self._list("GET", "/taxonomies/definitions")

    def get_taxonomy_definition(self, taxonomy_id: str) -> dict[str, Any]:
        return self._object("GET", f"/taxonomies/definitions/{taxonomy_id}")

    def create_taxonomy_entity(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._object("POST", "/taxonomies/entities", json=data)

    def list_taxonomy_entities(self, definition_id: str) -> list[dict[str, Any]]:
        return self._list("GET", f"/taxonomies/definitions/{definition_id}/entities")

    # Domain operations
    def create_domain_definition(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._object("POST", "/domains", json=data)

    def list_domain_definitions(self) -> list[dict[str, Any]]:
        return self._list("GET", "/domains")

    def get_domain_definition(self, domain_id: str) -> dict[str, Any]:
        return self._object("GET", f"/domains/{domain_id}")

    # Import operations
    def import_from_file(self, file_path: str, entity_type: str) -> dict[str, Any]:
        with open(file_path) as f:
            data = json.load(f)

        if entity_type == "company":
            return self.create_company(data)
        elif entity_type == "taxonomy":
            return self.create_taxonomy_definition(data)
        elif entity_type == "domain":
            return self.create_domain_definition(data)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
