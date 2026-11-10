# Goal: Application driven program and metrics

## Background

[ciqFE](git@github.com:venkykrishnan/ciqFE.git) is a prior iteration this zyPlat. *ciqFE* has the notion of program and metric rooted on a `ciq v2` grammar.
This grammar supports user's ability to create programs with metrics. It includes the ability to validate their grammar using a parser, bind them to domain data, calculate
bind data and persist the output. This implementation in *ciqFE*, as you can see in the repo, uses Parsimmon parser and is entirely in typescript.

### ciqFE with both system and configurable domains and taxonomies

*ciqFE* supports both system and configurable domains and taxonomies. In *zyPlat* I am eliminating this distinction. All domains and taxonomies are configured.
So *zyPlat* needs to stick to only configurable domains and taxonomies.

### Base & System program metrics

Given that all domains and taxonomies are configured in the scope of an application, the notion of a base program or a base metric is not needed in *zyPlat*.

### Evaluate the grammar

In *ciqFE* there are programs that use this ciq v2 grammar. There are also useful/valuable applications of this language for synamic calculations, customer
bookings, filters. All of them need to be supported in *zyPlat*.

Since this grammar is evolved from a v1 and has been put to use, review the grammar & provide any suggestions to improve.

Name this language in *zyPlat* as zml, i.e., short form for zyPlat metrics language.

### zyPlat Application enhanced with ideas from ciqLet

*ciqFE* also has the notion of a *ciqLet* which is an application that has input & output domains along with one or more programs.
*zyPlat* has the notion of an application as well. I would like the ciqLet notion to be implemented in zyPlat as application.

### Provided/pre-calculate vs calculated metric value

A metric value can be either calculated or provided. Some aspect of this notion exists in *ciqFE*. In *zyPlat* I want to make this as first class notion.
A metric value can be an input value in which case, the metric need not be calculated. This metric is a provided (aka pre-calculated) value.
The metric value can be also calculated (using metric formula). The metric service needs to be able to support both. 
For a time series, some portion of the metric values can be provided while some others are calculated. For example, the EBITDA metric for a borrower
for Jan 2026-Apr 2026 are provided while May 2026 onwards the metric is calculated. For the current scope, this provided vs calculated is at the program scope.
A program (and its collection of metrics) are scoped by a set of periods that have provided vs calculated.

*Note* there are other extensive features in *ciqFE*. I intend to transfer them over in stages to *zyPlat*. The focus in this goal is only programs and metrics. Since
*zyPlat* has no notion of system predefined domains and tazonomies and its scoped to an application. Application improvements to support programs and metrics are scoped here as well. A program (and its metrics) can be accessed by multiple application.
Some examples of applications are *FinancialStatements*, *TermLoan* which can use some of the programs in FinancialStatements.

## Open Questions

1. Based on above background, what is the recommendation on (if) any improvements to the grammar?
2. So *zyPlat* is based on pandas/python. *ciqFE* is based on typescript. The grammar is written in Parsimmon. For time series calculations (predominant value of zyPlat)
a dataframe output that can be efficiently accessed is important. With that in mind, domain instances are stored in parquet etc. What is the recommendation for this transfer over of this *ciq grammar* to *zyPlat* in terms of parser, programming framework, language?
3. There are other *dsl* languages in *ciqFE* that will be transfered over to *zyPlat*, please keep that in mind in this evaluation.
4. Based on above factors, the metrics service may have 2 distinct parts, the part to define, configure programs and metrics as well generate calculated values after a bind. Another part that is retrieving values (perhaps).

## Use cases to be supported

1. Replicate the use cases from *ciqFE* for use of this grammar.
2. Support a cli to import programs and metrics. There's no need to support metrics without a program scope. Ensure that both json & txt imports are consistent.

## Steps to be taken

1. Review the above descriptions
2. Address open questions and any other design questions.
3. Propose a plan and write the plan in this projects [plans](docs/plans folder). The plan needs to propose the programming language, framework, persisent store for this goal.
4. Get my input on the the proposed plan. Then update the goal, especially the
use cases to be supported, and the plans based on this review.
5. Implement the plan especially with unit and integration tests.
