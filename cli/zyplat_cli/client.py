import requests
from typing import Dict, Any, List, Optional
import json


class ZyPlatClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    # Company operations
    def create_company(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/companies", json=data).json()

    def list_companies(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/companies").json()

    def get_company(self, company_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/companies/{company_id}").json()

    def update_company(self, company_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/companies/{company_id}", json=data).json()

    def delete_company(self, company_id: str) -> None:
        self._request("DELETE", f"/companies/{company_id}")

    # Taxonomy operations
    def create_taxonomy_definition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/taxonomies/definitions", json=data).json()

    def list_taxonomy_definitions(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/taxonomies/definitions").json()

    def get_taxonomy_definition(self, taxonomy_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/taxonomies/definitions/{taxonomy_id}").json()

    def create_taxonomy_entity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/taxonomies/entities", json=data).json()

    def list_taxonomy_entities(self, definition_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/taxonomies/definitions/{definition_id}/entities").json()

    # Domain operations
    def create_domain_definition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/domains", json=data).json()

    def list_domain_definitions(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/domains").json()

    def get_domain_definition(self, domain_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/domains/{domain_id}").json()

    # Import operations
    def import_from_file(self, file_path: str, entity_type: str) -> Dict[str, Any]:
        with open(file_path, "r") as f:
            data = json.load(f)

        if entity_type == "company":
            return self.create_company(data)
        elif entity_type == "taxonomy":
            return self.create_taxonomy_definition(data)
        elif entity_type == "domain":
            return self.create_domain_definition(data)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
