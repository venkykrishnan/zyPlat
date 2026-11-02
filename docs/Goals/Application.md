# Goal: Notion of application

## Background

The *zyPlat*, as of **2 Nov 2026**, provides a platform for company, taxonomy and domains (along with domain instance). Refer to the zyPlat docs folder along with
source code for backend and cli.
This document introduces the notion of applications along with instantiation of companies, taxonomies and domains.

### Application

An application is an entity that has a configuration of domains. THe domains should exist prior creating an application.
A domain can be configured as an input or output entity.
An application has a name, description and version.

An application can be configured for multiple companies. For example,

 1. LoanMonitoring is an application that can be configured for NorthCo, SouthCo, WestCo and AllCo where AllCo is a lender and the rest are borrower company type.
 2. BBC is an application that's configured for NorthCo & WestCo and AllCo where AllCo is a lender and the rest are borrower company type.

The Application entity needs to support REST API for CRUD functionality.

A principal notion in *zyPlat* around time (period). There are 2 distinct notions in terms of time.

 1. Snapshot Period - This is currently implemented as company period. It supports period_type (which can be year, quarter, month, date).
 2. Time Series domain - A domain can be a time series, i.e., such a domain has a period field. Its domain instances are tabular with rows per period.
   *Note:* the below items are enhancements to the domain design and implementation and needs to be made as part of this goal.
   2.1. One of the fields in the domain needs to be identified as *the time series* field. This field has to have the data_type of `DATETIME`. There can be only one such field.
   2.2. Similar to the snapshot period, this time series field can be year, quarter, month, date. As part of this goal scope, this field needs to be validated (when domain instance is imported)
   in terms of its "period_type".

An application has a notion of a *bind instance*. There can be several bind instances for an application.
A bind instance is a set of domain instances for a company. This bind instance has a snapshot period. This snapshot is for most cases the company's snapshot period (id).
A bind instance in some situations may have its own snapshot period (over and above the company snapshot). An example is for the BBC where there may be multiple bind instances with the same company
snapshot period (example Jul 2026) and is delineated by the bind_snapshot (5Jul2026 and 15Jul2026).

## Open Questions

## Use cases to be supported

 1. CRUD REST API for Application. This includes validating the company information with the company service and domain with domain apis.
 2. Updates to the domain & domain instances to incorporate the changes proposed in the background section above.
 3. CRUD REST API for application bind instances. The application and bind instances can be distinct routes.

## Steps to be taken

1. Review the above descriptions
2. Address open questions and any other design questions to be addressed.
3. Propose a plan and write the plan in this projects [plans](docs/plans folder). The plan needs to propose the programming language, framework, persisent store for this goal.
4. Get my input on the the proposed plan. Then update the goal, especially the
use cases to be supported, and the plans based on this review.
5. Implement the plan especially with unit and integration tests.
