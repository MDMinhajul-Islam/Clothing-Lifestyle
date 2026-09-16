# Conversational catalogue search recovery

Latest verification: 375/375 offline tests passed after resolving sandbox temp
permissions. Real local catalogue (6,018 products / 6,018 stored vectors) exercised
the actual SQL and model: 12 queries took 0.023–0.516s after initialization. Added
fashion candidate filtering, query normalization, family aliases and ASR
clarification after observing furniture/perfume/toy false positives. See the
latest section in `docs/HANDOFF-semantic-search-2026-09-16.md` for measured examples
and remaining ambiguous-query relevance limitations. This supersedes the earlier
mock-only validation status below. No new image or production deployment yet.

Status: implemented locally; not committed, pushed, built, or deployed.

## Cause and scope

CatalogueRepository.search_products required PostgreSQL full-text matching before
vector distance ranking. A product with a different name/description could never
reach the ranking step when the words failed that lexical filter. The existing
query-relaxation fallback required a recognized product type/category, leaving
unrecognized names and broad descriptions without semantic recovery. Occasion
fallback also retained the failed lexical query. Some ordinary conversational
words survived facet parsing. Finally, "Please try" did not resume a search and
could reach the unconfigured general-chat LLM path.

These findings explain code paths reproduced locally, not a recovered trace of
the historical Retell call or a measurement of current production embeddings.

## Changes

- `backend/app/repositories/catalogue_repo.py`: optional semantic-only retrieval
  removes the lexical gate, requires an active product with a compatible stored
  embedding, filters by cosine similarity, then ranks by vector distance. Normal
  lexical retrieval is unchanged. Count and result queries use the same filter.
- `backend/app/services/catalogue_service.py`: after an empty exact search, retrieve
  semantic alternatives even without a recognized product type. Preserve department,
  category/id, product type, color, size, material, brand, price and sale filters.
  Occasion alternatives retain the original utterance embedding and are explicitly
  described as alternatives, not verified occasion-specific inventory. Remove common
  conversational fillers. Empty results ask what preference to broaden without
  inventing a color/budget preference or claiming products exist.
- `backend/app/voice/service.py`: short retries resume the preceding search without
  automatically clearing occasion, color, style or budget.
- Existing response composer already speaks up to three returned catalogue names
  and prices and offers details. No new generated products or prices are introduced.

Existing uncommitted ASR/voice changes were preserved. Authentication, order,
inventory, security, Retell transport, public listing queries and database schema
were not redesigned. The shared conversational filler parser also benefits public
search; the public catalogue tests passed.

## Verification

- New semantic recovery suite: 9/9 passed. Covers unknown product names, strict
  facet preservation, truthful empty results, absent embeddings, conversational
  fillers, SQL filters/parameter counts, exact-search preservation, and a multi-turn
  voice retry through routing/execution.
- Existing search-quality suite: 11/11 passed.
- Existing voice suites: 133/133 passed.
- Broad offline run: 369 tests attempted, 360 passed, 9 errored because Windows
  denied temporary-directory access. Affected tests: test_rag.test_immutable_capture
  and eight TestThroughputOptimizationComprehensive tests. No assertion failures.
  Two additional exact-search tests were added afterwards and passed in the 9-test
  targeted suite above. Counts overlap; do not sum suite totals.
- 15 live Tool Gateway API tests were excluded by the existing offline runner.
  psycopg2.connect was blocked during the broad run to prevent live database access.
- Python 3.11 parsing and git diff whitespace checks passed.
- Raw broad-run output: `tmp/semantic-regression-results.txt` (local, ignored).

## Remaining validation and risk

The semantic floor is 0.30 cosine similarity, following the existing policy-RAG
retriever convention. It is a relevance guard, not a calibrated product-quality
guarantee. Catalogue relevance, embedding coverage and query latency need a real
read-only database evaluation before production deployment. Current offline tests
use fake vectors/repositories and captured SQL; they do not prove live ranking
quality or database execution plans. Semantic retrieval adds a bounded fallback
query only after an exact miss, but database scan cost must still be measured.

Hard constraints remain authoritative: if no sufficiently similar product meets
them, the assistant asks permission to broaden instead of returning arbitrary
inventory. Embedding configuration/schema identity are unchanged. No new model,
LLM dependency, migration, container, image or deployment was introduced.

Production still runs the previously qualified recovery image. These local changes
are not included in it. Qualification and a controlled release are separate steps;
do not rebuild on the recovering VPS merely to apply this patch.
