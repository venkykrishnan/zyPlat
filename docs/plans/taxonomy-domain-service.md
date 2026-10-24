# Review and proposal: taxonomy and domain service

This is a review of [TaxonomyAndDomain.md](../Goals/TaxonomyAndDomain.md). It is not an implementation plan with settled tables. No service code belongs in the repo until this proposal has been reviewed and the ciqFE schemas have been read.

An earlier pass implemented a service before either of those happened. That code has been removed.

## Access check

Checked 24 October 2026, about 2:15pm Pacific.

This agent does not have access to ciqFE.

The cloud agent calls GitHub as the Cursor GitHub App installation, not as a personal login. That installation currently has one repository: `venkykrishnan/zyPlat`. This run's environment is also bound only to `github.com/venkykrishnan/zyplat`.

`GET /repos/venkykrishnan/ciqFE` returns 404. `git ls-remote https://github.com/venkykrishnan/ciqFE.git` returns "Repository not found." The same result comes back for `ciqfe`, `CIQFE`, and `ciq-fe`.

A 404 from this token means the app cannot see the repo. It does not distinguish "no such repo" from "private and not granted." Access that is visible in a browser session does not automatically extend to this installation.

To make the next pass able to read it:

1. On the GitHub account or organization that owns ciqFE, open Settings → Applications → Cursor → Configure.
2. Under Repository access, include `ciqFE`, or switch to All repositories, and save.
3. If ciqFE is owned by someone other than `venkykrishnan`, install the Cursor GitHub App on that owner as well.
4. If the repository name or owner is not `venkykrishnan/ciqFE`, send the exact `owner/name`.

After that, a new agent run should list ciqFE from `GET /installation/repositories`. This run's token still does not.

## Review of the goal

ciqFE is the source of the taxonomy and domain concepts. This service is a configurable version of those concepts, with a few stated differences:

- There is no separate class of standard taxonomies or domains. All of them are configuration.
- A taxonomy is hierarchical or flat. A hierarchical taxonomy has a root entity. `accountType` is the example of a hierarchy.
- An entity is a base entity unless it carries classifications. The classification list replaces ciqFE's `isSOR` boolean and is more general. The allowed names are configured on the taxonomy. Each entity holds some of those names.
- When a taxonomy is hierarchical, a parent's classifications are inherited by every descendant. The goal's example is `Revenue [CIQ, EDGAR]`: `Product Revenue` has at least `[CIQ, EDGAR]`. Storage may keep only the values assigned on an entity. The API still has to return the inherited result.
- A taxonomy carries configuration such as whether it is hierarchical, the allowed classifications, created and modified times, a version, and whether it is published. The service supports CRUD for the taxonomy and CRUD for its entities.
- A domain is also configuration. A dimension on a domain takes its legal values from one taxonomy's entities. The example is a general-ledger domain whose `accountType` dimension is the `accountType` taxonomy. The dimension records which taxonomy version it uses. That version is published. If the caller does not name one, the default is the latest published version.
- If a dimension's taxonomy has classifications, the domain inherits them. An instance of the domain says which of those classifications it uses. Only those, plus base entities, are legal values on that instance. The example is a general-ledger instance limited to `CIQ`: an `accountType` value is legal when it is base, or when it is classified as `CIQ`.

The use cases in the goal are CRUD for taxonomies and domains, CRUD for taxonomy entities, CRUD for a domain instance, and CRUD for the entities stored on that instance.

## What cannot be proposed yet

Open question 2 asks whether this model can carry ciqFE's taxonomies and domains, and what the input data has to change. That answer is a reading of ciqFE's types. A field list written without those types is a guess, and it is not possible to tell whether the guess matches the system this service is supposed to borrow from.

The same applies to the stack. The goal asks for a language, a framework, and a persistent store. The default should be ciqFE's language, framework, and store, unless the differences above force a split. Choosing those before reading the repo would define a second system beside ciqFE rather than a schema for it.

## What the ciqFE reading will produce

The next revision of this plan, once the repo is readable, will be a schema proposal in this form:

| ciqFE type | Fields that matter | What the goal changes |
| --- | --- | --- |
| filled from the code | filled from the code | filled from the goal |

The reading will look for:

- The taxonomy type and the taxonomy-entity type, including how a standard taxonomy differs from a configurable one.
- `isSOR` and any other per-entity flags that sit next to it.
- How a hierarchy is stored, whether a root is required, and whether more than one root occurs.
- Version, publish, created, and modified fields, if they exist, and what "version" identifies.
- The domain type, a dimension such as `inventoryClass` or `accountType`, and the reference from that dimension to a taxonomy.
- Whether ciqFE already separates a domain definition from an instance of that domain, and what a row inside an instance contains.
- The language, framework, and database those types already use.

That table is the schema proposal. It is also the answer to what ciqFE input data has to change.

## What can be said before that reading

These stay as requirements. They are not a table design.

1. Taxonomies and domains are configuration data. Nothing is built in.
2. Classification names are configured on the taxonomy. An entity holds a subset. Descendants keep the classifications of their ancestors. The API exposes that inherited set.
3. A domain dimension refers to one published taxonomy version.
4. A domain instance names which of the inherited classifications it uses. Base entities stay legal on every instance.
5. The service offers the four CRUD surfaces in the goal. It does not get built in the same step as this proposal.

Two rules in the goal are still open. ciqFE may already imply the answer, so they should be decided from the code when it is readable, and confirmed in review:

- An entity that carries more than one classification. The instance example says a value is legal when it is base or classified as `CIQ`. It does not say what happens when one entity is classified as both `CIQ` and `EDGAR` and the instance selected only `CIQ`.
- "Default is the latest published." That can mean the version number that was latest when the dimension was configured, stored and kept, or a live pointer that moves when a newer version is published.

## After review

When ciqFE is visible to this agent, the schema table above gets filled in and this plan is updated. Implementation stays the step after that review, which is step 5 in the goal.
