# Retrieval Architecture

GAIA uses a simple read-only retrieval pipeline.

## Steps

1. Classify the question.
2. Build search queries from the question and category.
3. Pull snapshot facts and Git facts.
4. Search the indexed MicroGrow documents.
5. Rank and deduplicate the evidence.
6. Assemble a bounded prompt context.
7. Produce a deterministic or provider-backed answer.

## Design goals

- Keep retrieval local.
- Keep evidence bounded and inspectable.
- Avoid exposing whole repository contents unnecessarily.
- Preserve read-only behavior.
