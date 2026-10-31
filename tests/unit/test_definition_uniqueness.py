"""Uniqueness of taxonomy and domain definitions across global and company scope.

Global rows have ``owner_company_id = NULL``. Postgres treats NULLs as distinct in a plain unique
constraint, so these rules need separate partial unique indexes per scope.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.company import Company, CompanyType
from backend.app.models.domain import DomainDefinition, DomainKind
from backend.app.models.taxonomy import DefinitionScope, TaxonomyDefinition


@pytest.fixture
def make_company(db_session):
    """Return a builder for persisted companies."""

    def build() -> Company:
        suffix = uuid.uuid4().hex[:8]
        company = Company(
            company_id=f"CO-{suffix}", name=f"Company {suffix}", company_type=CompanyType.LENDER
        )
        db_session.add(company)
        db_session.flush()
        return company

    return build


def _taxonomy(taxonomy_id="tax", version="1.0.0", owner=None, is_default=False):
    return TaxonomyDefinition(
        taxonomy_id=taxonomy_id,
        version=version,
        scope_type=DefinitionScope.COMPANY if owner else DefinitionScope.GLOBAL,
        owner_company_id=owner.id if owner else None,
        description="Test taxonomy",
        is_default=is_default,
    )


def _domain(domain_id="dom", owner=None):
    return DomainDefinition(
        domain_id=domain_id,
        description="Test domain",
        kind=DomainKind.TIME_SERIES,
        scope_type=DefinitionScope.COMPANY if owner else DefinitionScope.GLOBAL,
        owner_company_id=owner.id if owner else None,
    )


class TestTaxonomyVersionUniqueness:
    """A taxonomy id and version may exist once per scope owner."""

    def test_duplicate_global_version_is_rejected(self, db_session):
        """Global rows share a NULL owner, which a plain unique constraint ignores."""
        db_session.add(_taxonomy())
        db_session.flush()
        db_session.add(_taxonomy())

        with pytest.raises(IntegrityError, match="uq_taxonomy_definitions_global"):
            db_session.flush()

    def test_duplicate_version_for_one_company_is_rejected(self, db_session, make_company):
        """The same company cannot define the same taxonomy version twice."""
        company = make_company()
        db_session.add(_taxonomy(owner=company))
        db_session.flush()
        db_session.add(_taxonomy(owner=company))

        with pytest.raises(IntegrityError, match="uq_taxonomy_definitions_company"):
            db_session.flush()

    def test_same_version_for_different_companies_is_allowed(self, db_session, make_company):
        """Companies own separate namespaces."""
        db_session.add_all([_taxonomy(owner=make_company()), _taxonomy(owner=make_company())])

        db_session.flush()

    def test_same_version_in_global_and_company_scope_is_allowed(self, db_session, make_company):
        """A company may define its own taxonomy with a global taxonomy's id."""
        db_session.add_all([_taxonomy(), _taxonomy(owner=make_company())])

        db_session.flush()

    def test_different_versions_are_allowed(self, db_session):
        """Versions of one taxonomy coexist."""
        db_session.add_all([_taxonomy(version="1.0.0"), _taxonomy(version="2.0.0")])

        db_session.flush()


class TestTaxonomyDefault:
    """At most one version of a taxonomy is the default in each scope."""

    def test_two_global_defaults_for_one_taxonomy_are_rejected(self, db_session):
        """Otherwise default resolution is ambiguous."""
        db_session.add_all(
            [
                _taxonomy(version="1.0.0", is_default=True),
                _taxonomy(version="2.0.0", is_default=True),
            ]
        )

        with pytest.raises(IntegrityError, match="uq_taxonomy_default"):
            db_session.flush()

    def test_two_defaults_for_one_company_taxonomy_are_rejected(self, db_session, make_company):
        """The rule applies within a company too."""
        company = make_company()
        db_session.add_all(
            [
                _taxonomy(version="1.0.0", owner=company, is_default=True),
                _taxonomy(version="2.0.0", owner=company, is_default=True),
            ]
        )

        with pytest.raises(IntegrityError, match="uq_taxonomy_default"):
            db_session.flush()

    def test_defaults_in_separate_scopes_are_allowed(self, db_session, make_company):
        """Global and each company can have their own default."""
        db_session.add_all(
            [
                _taxonomy(is_default=True),
                _taxonomy(owner=make_company(), is_default=True),
                _taxonomy(owner=make_company(), is_default=True),
            ]
        )

        db_session.flush()

    def test_defaults_for_different_taxonomies_are_allowed(self, db_session):
        """The rule is per taxonomy id."""
        db_session.add_all([_taxonomy("a", is_default=True), _taxonomy("b", is_default=True)])

        db_session.flush()

    def test_non_default_versions_are_unrestricted(self, db_session):
        """Only the default flag is constrained."""
        db_session.add_all(
            [
                _taxonomy(version="1.0.0", is_default=True),
                _taxonomy(version="2.0.0"),
                _taxonomy(version="3.0.0"),
            ]
        )

        db_session.flush()


class TestDomainUniqueness:
    """A domain id may exist once per scope owner."""

    def test_duplicate_global_domain_is_rejected(self, db_session):
        """Global rows share a NULL owner, which a plain unique constraint ignores."""
        db_session.add(_domain())
        db_session.flush()
        db_session.add(_domain())

        with pytest.raises(IntegrityError, match="uq_domain_definitions_global"):
            db_session.flush()

    def test_duplicate_domain_for_one_company_is_rejected(self, db_session, make_company):
        """The same company cannot define a domain id twice."""
        company = make_company()
        db_session.add(_domain(owner=company))
        db_session.flush()
        db_session.add(_domain(owner=company))

        with pytest.raises(IntegrityError, match="uq_domain_definitions_company"):
            db_session.flush()

    def test_same_domain_for_different_companies_is_allowed(self, db_session, make_company):
        """Companies own separate namespaces."""
        db_session.add_all([_domain(owner=make_company()), _domain(owner=make_company())])

        db_session.flush()

    def test_same_domain_in_global_and_company_scope_is_allowed(self, db_session, make_company):
        """A company may define its own domain with a global domain's id."""
        db_session.add_all([_domain(), _domain(owner=make_company())])

        db_session.flush()
