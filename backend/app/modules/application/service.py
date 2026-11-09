"""Application lifecycle, enablement, and bind-instance orchestration."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from ...core.exceptions import ConflictError, NotFoundError, ValidationError
from ...crud import company as company_crud
from ...crud import domain as domain_crud
from ...models.application import (
    Application,
    ApplicationBindInstance,
    ApplicationBindInstanceMember,
    ApplicationCompany,
    ApplicationDomain,
    ApplicationDomainRole,
    ApplicationStatus,
    ApplicationVersion,
    SnapshotAlignment,
)
from ...models.company import Company, CompanySnapshot, PeriodGranularity
from ...models.domain import DomainDefinition, DomainInstance, DomainInstanceSnapshot
from ...models.taxonomy import TaxonomyDefinition
from .schemas import (
    ApplicationCompanyResponse,
    ApplicationCreate,
    ApplicationDomainCreate,
    ApplicationDomainResponse,
    ApplicationSummaryResponse,
    ApplicationVersionCreate,
    ApplicationVersionResponse,
    ApplicationVersionUpdate,
    BindInstanceCreate,
    BindInstanceResponse,
    BindInstanceUpdate,
    BindMemberCreate,
    BindMemberResponse,
)
from .validators import company_snapshot_period, period_contained, validate_expected_against_domain


def _app_query(db: Session):
    return db.query(Application).options(
        selectinload(Application.versions).selectinload(ApplicationVersion.domains),
        selectinload(Application.default_version),
    )


def _version_query(db: Session):
    return db.query(ApplicationVersion).options(
        selectinload(ApplicationVersion.domains),
        selectinload(ApplicationVersion.application),
        selectinload(ApplicationVersion.companies),
        selectinload(ApplicationVersion.bind_instances).selectinload(
            ApplicationBindInstance.members
        ),
    )


def get_application(db: Session, application_id: str) -> Application:
    app = cast(
        Application | None,
        _app_query(db).filter(Application.application_id == application_id).one_or_none(),
    )
    if app is None:
        raise NotFoundError(f"Application '{application_id}' not found.")
    return app


def _require_writable(app: Application) -> None:
    if app.status == ApplicationStatus.ARCHIVED:
        raise ConflictError(f"Application '{app.application_id}' is ARCHIVED and read-only.")


def _version_response(app: Application, version: ApplicationVersion) -> ApplicationVersionResponse:
    domain_rows: list[ApplicationDomainResponse] = []
    session = Session.object_session(version)
    for row in version.domains:
        domain_id = getattr(row, "_domain_id", None)
        if domain_id is None and session is not None:
            definition = session.get(DomainDefinition, row.domain_definition_id)
            domain_id = definition.domain_id if definition else str(row.domain_definition_id)
        domain_rows.append(
            ApplicationDomainResponse(
                id=row.id,
                domain_definition_id=row.domain_definition_id,
                domain_id=domain_id or str(row.domain_definition_id),
                role=row.role,
                snapshot_alignment=row.snapshot_alignment,
                schema_hash=row.schema_hash,
            )
        )
    return ApplicationVersionResponse(
        id=version.id,
        application_id=app.application_id,
        version=version.version,
        name=version.name,
        description=version.description,
        status=app.status,
        is_default=app.default_version_id == version.id,
        domains=domain_rows,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _resolve_domain(db: Session, spec: ApplicationDomainCreate) -> DomainDefinition:
    domain = domain_crud.get_domain_definition_by_logical_id(
        db, spec.domain_id, owner_company_id=spec.owner_company_id
    )
    if domain is None:
        raise NotFoundError(f"Domain '{spec.domain_id}' not found.")
    # Taxonomy-backed expected dimensions must resolve to a published taxonomy when named.
    for dim in spec.expected.dimensions:
        if dim.taxonomy_id is None:
            continue
        query = db.query(TaxonomyDefinition).filter(
            TaxonomyDefinition.taxonomy_id == dim.taxonomy_id,
            TaxonomyDefinition.is_published.is_(True),
        )
        if dim.taxonomy_version is not None:
            query = query.filter(TaxonomyDefinition.version == dim.taxonomy_version)
        if query.first() is None:
            raise ValidationError(
                f"Taxonomy '{dim.taxonomy_id}' "
                f"{'version ' + dim.taxonomy_version if dim.taxonomy_version else ''} "
                "is missing or unpublished."
            )
    return domain


def _build_domain_rows(
    db: Session, specs: list[ApplicationDomainCreate]
) -> list[ApplicationDomain]:
    rows: list[ApplicationDomain] = []
    seen: set[UUID] = set()
    for spec in specs:
        domain = _resolve_domain(db, spec)
        domain_uuid = cast(UUID, domain.id)
        if domain_uuid in seen:
            raise ValidationError(
                f"Domain '{spec.domain_id}' is listed more than once in the application."
            )
        seen.add(domain_uuid)
        schema_hash = validate_expected_against_domain(domain, spec.expected)
        row = ApplicationDomain(
            domain_definition_id=domain_uuid,
            role=spec.role,
            snapshot_alignment=spec.snapshot_alignment,
            schema_hash=schema_hash,
        )
        row._domain_id = cast(str, domain.domain_id)
        rows.append(row)
    return rows


def create_application(db: Session, payload: ApplicationCreate) -> ApplicationVersionResponse:
    existing = (
        db.query(Application)
        .filter(Application.application_id == payload.application_id)
        .one_or_none()
    )
    if existing is not None:
        raise ConflictError(f"Application '{payload.application_id}' already exists.")

    app = Application(application_id=payload.application_id, status=ApplicationStatus.DRAFT)
    version = ApplicationVersion(
        version=payload.version,
        name=payload.name,
        description=payload.description,
        domains=_build_domain_rows(db, payload.domains),
    )
    app.versions.append(version)
    db.add(app)
    db.flush()
    app.default_version_id = version.id
    db.commit()
    app = get_application(db, payload.application_id)
    version = next(v for v in app.versions if v.id == app.default_version_id)
    return _version_response(app, version)


def add_version(
    db: Session, application_id: str, payload: ApplicationVersionCreate
) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    _require_writable(app)
    if any(v.version == payload.version for v in app.versions):
        raise ConflictError(
            f"Version '{payload.version}' already exists for application '{application_id}'."
        )
    version = ApplicationVersion(
        application_id=app.id,
        version=payload.version,
        name=payload.name,
        description=payload.description,
        domains=_build_domain_rows(db, payload.domains),
    )
    db.add(version)
    db.flush()
    app.default_version_id = version.id
    db.commit()
    app = get_application(db, application_id)
    version = next(v for v in app.versions if v.version == payload.version)
    return _version_response(app, version)


def list_applications(
    db: Session,
    *,
    application_id: str | None = None,
    status: ApplicationStatus | None = None,
) -> list[ApplicationSummaryResponse]:
    query = db.query(Application).options(selectinload(Application.default_version))
    if application_id:
        query = query.filter(Application.application_id == application_id)
    if status:
        query = query.filter(Application.status == status)
    rows = query.order_by(Application.application_id).all()
    result: list[ApplicationSummaryResponse] = []
    for app in rows:
        default_version = app.default_version.version if app.default_version else None
        result.append(
            ApplicationSummaryResponse(
                id=app.id,
                application_id=app.application_id,
                status=app.status,
                default_version=default_version,
                created_at=app.created_at,
                updated_at=app.updated_at,
            )
        )
    return result


def get_default_version(db: Session, application_id: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    if app.default_version_id is None:
        raise NotFoundError(f"Application '{application_id}' has no default version.")
    version = next((v for v in app.versions if v.id == app.default_version_id), None)
    if version is None:
        raise NotFoundError(f"Default version for '{application_id}' is missing.")
    return _version_response(app, version)


def get_version(db: Session, application_id: str, version: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    return _version_response(app, match)


def update_version(
    db: Session, application_id: str, version: str, payload: ApplicationVersionUpdate
) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(match, field, value)
    db.commit()
    return get_version(db, application_id, version)


def set_default(db: Session, application_id: str, version: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    app.default_version_id = match.id
    db.commit()
    return get_version(db, application_id, version)


def publish(db: Session, application_id: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    if app.status != ApplicationStatus.DRAFT:
        raise ConflictError(
            f"Application '{application_id}' must be DRAFT to publish; is {app.status.value}."
        )
    app.status = ApplicationStatus.PUBLISHED
    db.commit()
    return get_default_version(db, application_id)


def unpublish(db: Session, application_id: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    if app.status != ApplicationStatus.PUBLISHED:
        raise ConflictError(
            f"Application '{application_id}' must be PUBLISHED to unpublish; is {app.status.value}."
        )
    bind_count = (
        db.query(ApplicationBindInstance)
        .join(ApplicationVersion)
        .filter(ApplicationVersion.application_id == app.id)
        .count()
    )
    if bind_count:
        raise ConflictError(
            f"Cannot unpublish '{application_id}' while bind instances exist; archive instead."
        )
    app.status = ApplicationStatus.DRAFT
    db.commit()
    return get_default_version(db, application_id)


def archive(db: Session, application_id: str) -> ApplicationVersionResponse:
    app = get_application(db, application_id)
    app.status = ApplicationStatus.ARCHIVED
    db.commit()
    return get_default_version(db, application_id)


def delete_version(db: Session, application_id: str, version: str) -> None:
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    if match.bind_instances:
        raise ConflictError(f"Cannot delete version '{version}' while bind instances exist.")
    if app.default_version_id == match.id:
        raise ConflictError(
            f"Cannot delete the default version '{version}'; set another default first."
        )
    db.delete(match)
    db.commit()


def enable_company(
    db: Session, application_id: str, version: str, company_logical_id: str
) -> ApplicationCompanyResponse:
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    company = company_crud.get_company_by_company_id(db, company_logical_id)
    if company is None:
        raise NotFoundError(f"Company '{company_logical_id}' not found.")
    existing = (
        db.query(ApplicationCompany)
        .filter(
            ApplicationCompany.application_version_id == match.id,
            ApplicationCompany.company_id == company.id,
        )
        .one_or_none()
    )
    if existing is None:
        existing = ApplicationCompany(application_version_id=match.id, company_id=company.id)
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return ApplicationCompanyResponse(
        company_id=cast(str, company.company_id),
        company_uuid=cast(UUID, company.id),
        created_at=existing.created_at,
    )


def list_companies(
    db: Session, application_id: str, version: str
) -> list[ApplicationCompanyResponse]:
    app = get_application(db, application_id)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    rows = (
        db.query(ApplicationCompany, Company)
        .join(Company, Company.id == ApplicationCompany.company_id)
        .filter(ApplicationCompany.application_version_id == match.id)
        .all()
    )
    return [
        ApplicationCompanyResponse(
            company_id=company.company_id,
            company_uuid=company.id,
            created_at=link.created_at,
        )
        for link, company in rows
    ]


def disable_company(
    db: Session, application_id: str, version: str, company_logical_id: str
) -> None:
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    company = company_crud.get_company_by_company_id(db, company_logical_id)
    if company is None:
        raise NotFoundError(f"Company '{company_logical_id}' not found.")
    binds = (
        db.query(ApplicationBindInstance)
        .filter(
            ApplicationBindInstance.application_version_id == match.id,
            ApplicationBindInstance.company_id == company.id,
        )
        .count()
    )
    if binds:
        raise ConflictError(
            f"Cannot disable company '{company_logical_id}' while bind instances exist."
        )
    link = (
        db.query(ApplicationCompany)
        .filter(
            ApplicationCompany.application_version_id == match.id,
            ApplicationCompany.company_id == company.id,
        )
        .one_or_none()
    )
    if link is None:
        raise NotFoundError(
            f"Company '{company_logical_id}' is not enabled on '{application_id}'@{version}."
        )
    db.delete(link)
    db.commit()


def add_output_domain(
    db: Session, application_id: str, version: str, spec: ApplicationDomainCreate
) -> ApplicationDomainResponse:
    if spec.role != ApplicationDomainRole.OUTPUT:
        raise ValidationError("Only OUTPUT domains can be added after create.")
    app = get_application(db, application_id)
    _require_writable(app)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    rows = _build_domain_rows(db, [spec])
    row = rows[0]
    row.application_version_id = match.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApplicationDomainResponse(
        id=row.id,
        domain_definition_id=row.domain_definition_id,
        domain_id=getattr(row, "_domain_id", spec.domain_id),
        role=row.role,
        snapshot_alignment=row.snapshot_alignment,
        schema_hash=row.schema_hash,
    )


def list_domains(db: Session, application_id: str, version: str) -> list[ApplicationDomainResponse]:
    return get_version(db, application_id, version).domains


def _resolve_bind_company_snapshot(
    db: Session, company: Company, payload: BindInstanceCreate
) -> CompanySnapshot:
    company_uuid = cast(UUID, company.id)
    if payload.company_snapshot_id is not None:
        return company_crud.get_company_snapshot(db, company_uuid, payload.company_snapshot_id)
    if payload.period_type is None or not payload.period_value:
        raise ValidationError("Provide company_snapshot_id or both period_type and period_value.")
    return company_crud.get_default_company_snapshot(
        db, company_uuid, payload.period_type, payload.period_value
    )


def _member_responses(db: Session, bind: ApplicationBindInstance) -> list[BindMemberResponse]:
    result: list[BindMemberResponse] = []
    for member in bind.members:
        definition = db.get(DomainDefinition, member.domain_definition_id)
        domain_id = (
            cast(str, definition.domain_id)
            if definition is not None
            else str(member.domain_definition_id)
        )
        result.append(
            BindMemberResponse(
                domain_id=domain_id,
                domain_definition_id=member.domain_definition_id,
                domain_instance_snapshot_id=member.domain_instance_snapshot_id,
            )
        )
    return result


def _bind_response(
    db: Session,
    app: Application,
    version: ApplicationVersion,
    bind: ApplicationBindInstance,
) -> BindInstanceResponse:
    company = db.get(Company, bind.company_id)
    snapshot = db.get(CompanySnapshot, bind.company_snapshot_id)
    assert company is not None and snapshot is not None
    return BindInstanceResponse(
        id=bind.id,
        application_id=app.application_id,
        version=version.version,
        company_id=cast(str, company.company_id),
        company_snapshot_id=cast(UUID, snapshot.id),
        period_type=snapshot.period_type,
        period_value=str(snapshot.period_value),
        members=_member_responses(db, bind),
        created_at=bind.created_at,
        updated_at=bind.updated_at,
    )


def _validate_and_build_members(
    db: Session,
    version: ApplicationVersion,
    company: Company,
    snapshot: CompanySnapshot,
    members: list[BindMemberCreate],
    *,
    resolve_independent: bool,
) -> list[ApplicationBindInstanceMember]:
    # Keyed by domain logical id via definition lookup.
    app_domains: dict[str, ApplicationDomain] = {}
    definition_by_logical: dict[str, DomainDefinition] = {}
    for app_domain in version.domains:
        definition = db.get(DomainDefinition, app_domain.domain_definition_id)
        if definition is None:
            raise NotFoundError(f"Domain definition {app_domain.domain_definition_id} missing.")
        definition_by_logical[str(definition.domain_id)] = definition
        app_domains[str(definition.domain_id)] = app_domain

    built: list[ApplicationBindInstanceMember] = []
    company_tied_seen: set[str] = set()

    for member in members:
        app_domain = app_domains.get(member.domain_id)
        if app_domain is None:
            raise ValidationError(
                f"Domain '{member.domain_id}' is not part of this application version."
            )
        definition = definition_by_logical[member.domain_id]
        snap = db.get(DomainInstanceSnapshot, member.domain_instance_snapshot_id)
        if snap is None:
            raise NotFoundError(
                f"Domain instance snapshot {member.domain_instance_snapshot_id} not found."
            )
        instance = db.get(DomainInstance, snap.domain_instance_id)
        if instance is None or str(instance.company_id) != str(company.id):
            raise ValidationError(
                f"Snapshot {snap.id} does not belong to company '{company.company_id}'."
            )
        if instance.domain_definition_id != definition.id:
            raise ValidationError(f"Snapshot {snap.id} is not for domain '{member.domain_id}'.")

        if app_domain.snapshot_alignment == SnapshotAlignment.COMPANY:
            if snap.company_snapshot_id != snapshot.id:
                raise ValidationError(
                    f"Company-tied domain '{member.domain_id}' snapshot must match the "
                    "bind company snapshot."
                )
            if (
                member.domain_id in company_tied_seen
                and app_domain.role == ApplicationDomainRole.INPUT
            ):
                raise ValidationError(
                    f"Company-tied INPUT domain '{member.domain_id}' may have only one member."
                )
            company_tied_seen.add(member.domain_id)
        else:
            # Cast: ORM Column stubs treat nullable FKs as non-optional without the SA plugin.
            independent_company_snap = cast(UUID | None, snap.company_snapshot_id)
            period_type = snap.snapshot_period_type
            if independent_company_snap is not None or period_type is None:
                raise ValidationError(
                    f"Independent domain '{member.domain_id}' requires an independent snapshot."
                )
            period_value = str(snap.snapshot_period_value) if snap.snapshot_period_value else ""
            outer_type, outer_value = company_snapshot_period(snapshot)
            if not period_contained(period_type, period_value, outer_type, outer_value):
                raise ValidationError(
                    f"Independent snapshot {period_value} is not contained in "
                    f"{outer_type.value} {outer_value}."
                )

        built.append(
            ApplicationBindInstanceMember(
                domain_definition_id=cast(UUID, definition.id),
                domain_instance_snapshot_id=cast(UUID, snap.id),
            )
        )

    # Ensure every company-tied INPUT has a member.
    for domain_id, app_domain in app_domains.items():
        if (
            app_domain.role == ApplicationDomainRole.INPUT
            and app_domain.snapshot_alignment == SnapshotAlignment.COMPANY
            and domain_id not in company_tied_seen
        ):
            raise ValidationError(f"Missing company-tied INPUT snapshot for domain '{domain_id}'.")

    if resolve_independent:
        outer_type, outer_value = company_snapshot_period(snapshot)
        existing_ids = {m.domain_instance_snapshot_id for m in built}
        for domain_id, app_domain in app_domains.items():
            if app_domain.snapshot_alignment != SnapshotAlignment.INDEPENDENT:
                continue
            if app_domain.role != ApplicationDomainRole.INPUT:
                continue
            definition = definition_by_logical[domain_id]
            instance = (
                db.query(DomainInstance)
                .filter(
                    DomainInstance.domain_definition_id == definition.id,
                    DomainInstance.company_id == company.id,
                )
                .one_or_none()
            )
            if instance is None:
                continue
            snaps = (
                db.query(DomainInstanceSnapshot)
                .filter(
                    DomainInstanceSnapshot.domain_instance_id == instance.id,
                    DomainInstanceSnapshot.company_snapshot_id.is_(None),
                )
                .all()
            )
            for snap in snaps:
                if snap.id in existing_ids:
                    continue
                if snap.snapshot_period_type is None:
                    continue
                period_value = str(snap.snapshot_period_value) if snap.snapshot_period_value else ""
                if period_contained(
                    snap.snapshot_period_type,
                    period_value,
                    outer_type,
                    outer_value,
                ):
                    snap_id = cast(UUID, snap.id)
                    built.append(
                        ApplicationBindInstanceMember(
                            domain_definition_id=cast(UUID, definition.id),
                            domain_instance_snapshot_id=snap_id,
                        )
                    )
                    existing_ids.add(snap_id)

    return built


def create_bind_instance(
    db: Session, application_id: str, version: str, payload: BindInstanceCreate
) -> BindInstanceResponse:
    app = get_application(db, application_id)
    if app.status != ApplicationStatus.PUBLISHED:
        raise ConflictError(
            f"Bind instances require PUBLISHED status; '{application_id}' is {app.status.value}."
        )
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    company = company_crud.get_company_by_company_id(db, payload.company_id)
    if company is None:
        raise NotFoundError(f"Company '{payload.company_id}' not found.")
    enabled = (
        db.query(ApplicationCompany)
        .filter(
            ApplicationCompany.application_version_id == match.id,
            ApplicationCompany.company_id == company.id,
        )
        .one_or_none()
    )
    if enabled is None:
        raise ConflictError(
            f"Company '{payload.company_id}' is not enabled on '{application_id}'@{version}."
        )
    snapshot = _resolve_bind_company_snapshot(db, company, payload)
    members = _validate_and_build_members(
        db,
        match,
        company,
        snapshot,
        payload.members,
        resolve_independent=payload.resolve_independent_members,
    )
    bind = ApplicationBindInstance(
        application_version_id=match.id,
        company_id=company.id,
        company_snapshot_id=snapshot.id,
        members=members,
    )
    db.add(bind)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ConflictError(
            "A bind instance already exists for this application, company, and snapshot."
        ) from exc
    loaded = (
        db.query(ApplicationBindInstance)
        .options(selectinload(ApplicationBindInstance.members))
        .filter(
            ApplicationBindInstance.application_version_id == match.id,
            ApplicationBindInstance.company_id == company.id,
            ApplicationBindInstance.company_snapshot_id == snapshot.id,
        )
        .one()
    )
    return _bind_response(db, app, match, loaded)


def list_bind_instances(
    db: Session,
    application_id: str,
    version: str,
    *,
    company_id: str | None = None,
    period_type: PeriodGranularity | None = None,
    period_value: str | None = None,
) -> list[BindInstanceResponse]:
    app = get_application(db, application_id)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    query = (
        db.query(ApplicationBindInstance)
        .options(selectinload(ApplicationBindInstance.members))
        .filter(ApplicationBindInstance.application_version_id == match.id)
    )
    if company_id:
        company = company_crud.get_company_by_company_id(db, company_id)
        if company is None:
            raise NotFoundError(f"Company '{company_id}' not found.")
        query = query.filter(ApplicationBindInstance.company_id == company.id)
    binds = query.all()
    results: list[BindInstanceResponse] = []
    for bind in binds:
        response = _bind_response(db, app, match, bind)
        if period_type and response.period_type != period_type:
            continue
        if period_value and response.period_value != period_value:
            continue
        results.append(response)
    return results


def get_bind_instance(
    db: Session, application_id: str, version: str, bind_instance_id: UUID
) -> BindInstanceResponse:
    app = get_application(db, application_id)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    bind = (
        db.query(ApplicationBindInstance)
        .options(selectinload(ApplicationBindInstance.members))
        .filter(
            ApplicationBindInstance.id == bind_instance_id,
            ApplicationBindInstance.application_version_id == match.id,
        )
        .one_or_none()
    )
    if bind is None:
        raise NotFoundError(f"Bind instance {bind_instance_id} not found.")
    return _bind_response(db, app, match, bind)


def update_bind_instance(
    db: Session,
    application_id: str,
    version: str,
    bind_instance_id: UUID,
    payload: BindInstanceUpdate,
) -> BindInstanceResponse:
    app = get_application(db, application_id)
    if app.status != ApplicationStatus.PUBLISHED:
        raise ConflictError(
            f"Bind instances require PUBLISHED status; '{application_id}' is {app.status.value}."
        )
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    bind = (
        db.query(ApplicationBindInstance)
        .options(selectinload(ApplicationBindInstance.members))
        .filter(
            ApplicationBindInstance.id == bind_instance_id,
            ApplicationBindInstance.application_version_id == match.id,
        )
        .one_or_none()
    )
    if bind is None:
        raise NotFoundError(f"Bind instance {bind_instance_id} not found.")
    company = db.get(Company, bind.company_id)
    snapshot = db.get(CompanySnapshot, bind.company_snapshot_id)
    assert company is not None and snapshot is not None
    # Only OUTPUT members may be replaced via update; merge with existing INPUT members.
    existing_inputs = []
    domain_by_def = {d.domain_definition_id: d for d in match.domains}
    for member in bind.members:
        app_domain = domain_by_def[member.domain_definition_id]
        if app_domain.role == ApplicationDomainRole.INPUT:
            definition = db.get(DomainDefinition, member.domain_definition_id)
            assert definition is not None
            existing_inputs.append(
                BindMemberCreate(
                    domain_id=cast(str, definition.domain_id),
                    domain_instance_snapshot_id=member.domain_instance_snapshot_id,
                )
            )
    for member in payload.members:
        app_domain = None
        for d in match.domains:
            definition = db.get(DomainDefinition, d.domain_definition_id)
            if definition and definition.domain_id == member.domain_id:
                app_domain = d
                break
        if app_domain is None or app_domain.role != ApplicationDomainRole.OUTPUT:
            raise ValidationError("Bind update may only attach OUTPUT domain members.")
    new_members = _validate_and_build_members(
        db,
        match,
        company,
        snapshot,
        existing_inputs + payload.members,
        resolve_independent=False,
    )
    bind.members.clear()
    db.flush()
    bind.members.extend(new_members)
    db.commit()
    return get_bind_instance(db, application_id, version, bind_instance_id)


def delete_bind_instance(
    db: Session, application_id: str, version: str, bind_instance_id: UUID
) -> None:
    app = get_application(db, application_id)
    match = next((v for v in app.versions if v.version == version), None)
    if match is None:
        raise NotFoundError(f"Application '{application_id}' version '{version}' not found.")
    bind = (
        db.query(ApplicationBindInstance)
        .filter(
            ApplicationBindInstance.id == bind_instance_id,
            ApplicationBindInstance.application_version_id == match.id,
        )
        .one_or_none()
    )
    if bind is None:
        raise NotFoundError(f"Bind instance {bind_instance_id} not found.")
    db.delete(bind)
    db.commit()
