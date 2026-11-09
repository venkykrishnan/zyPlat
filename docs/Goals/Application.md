# Goal: Notion of application

## Background

The *zyPlat*, as of **2 Nov 2026**, provides a platform for company, taxonomy and domains (along with domain instance). Refer to the zyPlat docs folder along with
source code for backend and cli.
This document introduces the notion of applications along with instantiation of companies, taxonomies and domains.

### Application

An application is an entity that has a configuration of domains. The domains should exist prior creating an application.
A domain can be configured as an input or output entity.
An application has a name, description and version. Versions belong to one logical
application (`application_id`). The logical application has a **status**
(Draft / Publish / Archive) and a **default version** pointer: creating a new version
makes it the default; an explicit API can set default to any version; default is
independent of status (a Draft application still has a default). `GET` by application id
returns the default version. Bind-instance writes are allowed only when the application is
Published.

An application can be configured for multiple companies. For example,

 1. LoanMonitoring is an application that can be configured for NorthCo, SouthCo, WestCo and AllCo where AllCo is a lender and the rest are borrower company type.
 2. BBC is an application that's configured for NorthCo & WestCo and AllCo where AllCo is a lender and the rest are borrower company type.

The Application entity needs to support REST API for CRUD functionality.

A principal notion in *zyPlat* around time (period). There are 2 distinct notions in terms of time.

 1. Snapshot Period - This is currently implemented as company period. It supports period_type (which can be year, quarter, month, date).
 2. Time Series domain - A domain can be a time series, i.e., such a domain has a period field. Its domain instances are tabular with rows per period.
   2.1. One of the fields in the domain needs to be identified as *the time series* field (`is_time_series` + `period_type`). This field has to have the data_type of `DATETIME`. There can be only one such field.
   2.2. Similar to the snapshot period, this time series field can be year, quarter, month, date. Import validation requires UTC midnight at period start.

An application has a notion of a *bind instance*. There can be several bind instances for an application.
A bind instance is one **company-period view** (for example July 2026): company-tied domains contribute one snapshot each; independent domains (BBC) may contribute **many** date snapshots contained in that period as members — not one bind instance per BBC date.

## Decided answers (from plan review)

1. Routes: `/api/v1/applications/...` for definition/lifecycle; bind instances under
   `/versions/{version}/bind-instances`.
2. Create validates a required subset of the live domain schema and does not create domains.
3. Applications are global; status on the logical app; default version pointer with auto-default
   on create and explicit set-default; GET by id returns default.
4. BBC-like domains use `snapshot_alignment = INDEPENDENT` with null `company_snapshot_id`.
5. Bind writes require `PUBLISHED`.
6. Full design: `docs/plans/application-service.plan.md`.

## Use cases to be supported

 1. CRUD REST API for Application. This includes validating the company information with the company service and domain with domain apis.
 2. Default version: auto-default on new version; explicit set-default; get-by-id returns the default version.
 3. Application lifecycle at the logical application level: Draft → Publish → Archive (and unpublish when no bind instances exist); bind-instance writes only when Published.
 4. Updates to the domain & domain instances to incorporate time-series field and independent snapshots.
 5. CRUD REST API for application bind instances (July-view containment for independent dates).
 6. CLI commands for create/list/publish/enable-company/create-bind-instance.

## Steps to be taken

1. Review the above descriptions — done.
2. Address open questions and any other design questions — decided in the plan.
3. Propose a plan — `docs/plans/application-service.plan.md`.
4. Get input and update goal/plan — done.
5. Break the work into manageable PRs — plan §10.
6. Identify separate PRs that modify existing entities — plan §10 (PR1, PR2, PR4).
7. Implement the plan with unit and integration tests — done on `feature/application-service`.
