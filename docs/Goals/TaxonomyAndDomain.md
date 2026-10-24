# Goal: A REST service where taxonomies and domains can be managed (CRUD)

## Background

[ciqFE](https://github.com/venkykrishnan/ciqFE) is an application with backend
services that support a wide range of funcitonalities.
The focus of this document is on taxonomies and domains service borrowing on the concepts in the *ciqFE* work.
There are some key differences in this current proposal.

* All taxonomies and domains are configurable, in other words, there is no notion of concept of standard taxonomies, domains.
* Taxonomies
  * A taxonomy can be hierarchical (or not). An example of a hiearchical taxonomy is accountType.
  * If a taxonomy is hierarchical, there needs to be a root entity.
  * An entity by default is a base entity.
  * A taxonomy needs to support a classification field (per entity). This replaces the isSOR boolean in ciqFE and
  makes it more general.
  * A taxonomy can support multiple named classification values. The classification values are strings. These values allowed are configured at the taxonomy level. Each entity can have a list of these values in their classification field.
    * If a taxonomy isHierarchical, then if a parent entity has values in its classification field then all its descendants will inherit and have the same classification.
    * For example, if there is a Revenue entity with the classification fields of [CIQ, EDGAR] and a child Product Revenue needs to have at a minimum [CIQ, EDGAR] classification. 
    * The underlying implementation can make this inherent assumption that classifications are additive to an entity's
    descendents (they dont need to be explicity stored). The API should however support this logic.
  * Therefore, a taxonomy when created will have some configurations, for example, ishierachical, the range of classifications supported, create time, modified time, version, isPublished etc.
  * Taxonomy service needs to support CRUD.
  * A Taxonomy (much like ciqFE) needs to support CRUD of taxonomy entities.
* Domains
  * Much like taxonomy, all domains are configurable (CRUD).
  * A domain (like configurable domain like ciqFE, example inventory domain's inventoryClass) can have a dimension that's a taxonomy and its valid values are from that taxonomie's entities. For example, if its a general ledge domain and it
  has an accountType dimension. This dimension can be configured with a taxonomy named accountType (that was configured in the system). The values in that field need to be valid entries in the taxonomy. Also, when a taxonomy is configured for such a dimension, the version needs to be identified (default is the latest published). The version needs to be published.
  * If the domain includes a dimension that has classifications, then this domain inherits those classification values.
  * The domain, when instantiated, needs to indicate which of the classfications are configured for this instance. Only those are valid entries for that instantiation.
    * For example, a genernal ledger (GL) domain an it uses the AccountType taxonomy and that taxonomy has classifications of CIQ and EDGAR.
    * An instantiation of this gl domain can be configured to be only CIQ (and of course base).
    * Then entities in that instance can accountType values that are either base (no classification) or one of accountTypes that are classified as CIQ.

## Open Questions

1. What is the recommended structure for supporting taxonomy and domain services as described above?
2. Is this proposed solution going to be able to support ciqFE's taxonomy and domains? What changes do the input
data (from ciqFE) need?

## Use cases to be supported

1. A CRUD API for taxonomy & domains
2. A CRUD for instantiating entities for taxonomy
3. A CRUD for instantiating a domain.
4. A CRUD for entities in that domain's instance.

## Steps to be taken

1. Review the above descriptions
2. Address open questions and any other design questions to be addressed.
3. Propose a plan and write the plan in this projects [plans](docs/plans folder). The plan needs to propose the programming language, framework, persisent store for this goal.
4. Get my input on the the proposed plan. Then update the goal, especially the
use cases to be supported, and the plans based on this review.
5. Implement the plan especially with unit and integration tests.
