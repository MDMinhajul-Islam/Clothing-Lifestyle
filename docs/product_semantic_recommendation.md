# Product semantic recommendation — Phase 2E code handoff

Status: code ready for manual execution. Migration 009 is not applied, catalogue embeddings are not generated/imported, and runtime evaluation is not executed by Codex.

## Architecture

The product semantic layer is separate from official-policy RAG. `product_embeddings` references the real `products` table and stores one normalized 384-dimensional MiniLM vector per product. It is backend-only under RLS. The local model is `sentence-transformers/all-MiniLM-L6-v2`, provider `local_sentence_transformers`, version `v1`; CUDA is automatic when available and CPU is supported.

Embedding text deterministically includes only present catalogue fields: exact product name, department, sorted categories, sorted colors, composition, material, description, and fit. It excludes price, stock, images, synthetic operations, and inferred style attributes. SHA-256 of this text drives idempotent regeneration and import.

The generator reads all 6,018 products in one catalogue query, embeds changed texts in batches, writes an atomic local JSONL artifact, and reports embedded/skipped/failed counts. Import uses batched PostgreSQL upserts and skips matching hashes/model versions. The generated JSONL is gitignored.

The internal service supports `semantic_product_search`, `find_similar_products`, and `recommend_matching_products`. Two authenticated read-only gateway tools expose reference-product similarity and outfit matching. SQL enforces active products, the 384-dimensional model identity, self-exclusion, category/department/price/size/color filters, and cosine ranking. The service defensively reapplies requested filters.

Recommendation score is bounded cosine similarity plus 0.05 for verified availability and 0.01 for sale status. Category and requested color are filters, not invented fashion claims. Availability is verified through the existing `InventoryService` and explicitly labelled `synthetic_operational_layer`. Current price, variants, and availability remain database-backed; embeddings are never authoritative for them. Results are structured and contain reason codes without generated fashion prose.

## Manual VS Code PowerShell runbook

Run every command from `F:\NEXVIX INTERN\Clothing Lifestyle`. Stop at the first failure.

### 1. Check/install the local dependency

**Command**

```powershell
python -m pip install -r requirements-rag.txt
python -c "import torch; from sentence_transformers import SentenceTransformer; m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', local_files_only=True); print({'device':'cuda' if torch.cuda.is_available() else 'cpu','dimension':m.get_embedding_dimension()})"
```

**Does:** Confirms the free local model runtime and cached model. **Success:** installation succeeds and prints dimension `384` with `cpu` or `cuda`. **If it fails, send:** both commands, the last 30–50 output lines, and the traceback. If only the cache check fails, say whether Phase 2D.1 was run on this Windows user profile.

### 2. Verify backend database configuration

**Command**

```powershell
python -c "from backend.app.config import settings; print({'SUPABASE_DB_URL_configured':bool(settings.supabase_db_url)})"
```

**Does:** Checks ignored `.env` loading without printing the secret. **Success:** `True`. **If it fails, send:** the command and traceback; do not send the URL or `.env` contents.

### 3. Apply migration 009

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --apply-migration
```

**Does:** Creates the backend-only `product_embeddings` table and indexes. **Success:** `{'migration': '009_product_semantic_schema.sql', 'status': 'APPLIED'}`. **If it fails, send:** command, last 30–50 lines, traceback, and SQLSTATE if shown.

### 4. Dry-run source construction

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --dry-run
```

**Does:** Reads catalogue data, constructs/hashes texts, and performs no model load or database write. **Success:** `products: 6018`, `model_not_loaded: True`, `database_writes: False`; `unique_hashes` is informational because distinct product IDs may produce identical embedding text. **If it fails, send:** command, complete result/traceback, and reported product/hash counts.

### 5. Generate the 6,018 local embeddings

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --generate --batch-size 64
```

**Does:** Runs batched local CPU/CUDA inference and writes the ignored JSONL artifact. **Success:** final counts total 6,018 with `failed: 0` and `output_records: 6018`; a rerun may report unchanged products as skipped. **If it fails, send:** command, last 30–50 lines, traceback, final counts, and the last progress line.

### 6. Verify the local artifact

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --verify-output
```

**Does:** Validates IDs, hashes, model metadata, vectors, and dimensions without connecting to Supabase. **Success:** `output_records: 6018`, `valid_embeddings: 6018`, `dimension: 384`. **If it fails, send:** command, traceback, and reported counts; do not edit the JSONL manually.

### 7. Import/upsert to Supabase

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --import --batch-size 200
```

**Does:** Batched idempotent upserts into `product_embeddings`. **Success:** first run normally reports `upserted: 6018`, `failed: 0`; rerun normally reports `upserted: 0`, `skipped: 6018`. **If it fails, send:** command, last 30–50 lines, traceback/SQLSTATE, and last upsert progress/count.

### 8. Verify Supabase counts and dimensions

**Command**

```powershell
python -m scripts.zara_recommendation.generate_product_embeddings --verify-db
```

**Does:** Verifies the chosen model/version rows and vector dimensions. **Success:** `product_embeddings: 6018`, `embedded_chunks: 6018`, min/max dimension `384`. **If it fails, send:** command, complete printed count result, and traceback.

### 9. Run focused recommendation tests

**Command**

```powershell
python -m unittest tests.test_recommendation -v
```

**Does:** Tests deterministic text/hash behavior, filters, self-exclusion, IDs, schemas, and the availability boundary. **Success:** all 5 tests pass. **If it fails, send:** command, failed test names, assertion text, and traceback.

### 10. Run the read-only recommendation evaluation

**Command**

```powershell
python -m scripts.zara_recommendation.evaluate_recommendations
```

**Does:** Runs four constrained semantic searches in a read-only transaction and verifies category, price, IDs, and inventory-boundary fields. **Success:** `passed: 4`, `total: 4`. **If it fails, send:** command, complete JSON result, last 30–50 lines, and traceback.

### 11. Run the established safe regression subset

**Command**

```powershell
python -m scripts.zara_knowledge.run_safe_tests
```

**Does:** Runs local tests while excluding live gateway integration methods that persist audit/mutation data. **Success:** approximately 90 tests run and the suite reports `OK`. **If it fails, send:** command, failed test names, last 50 lines, and traceback.

### 12. Review Git state

**Command**

```powershell
git status --short
git diff --check
git diff --stat
```

**Does:** Reviews the prepared code and whitespace before staging. **Success:** only intended Phase 2E files are changed and `git diff --check` is silent apart from line-ending warnings. **If it fails, send:** all three outputs.

### 13. Stage and commit after validation

**Command**

```powershell
git add .gitignore backend/app/api/routes_tools.py backend/app/recommendation backend/app/tools/definitions.json backend/app/tools/registry.py docs/product_semantic_recommendation.md scripts/zara_recommendation supabase/migrations/009_product_semantic_schema.sql tests/test_recommendation.py
git commit -m "feat(recommendation): add product semantic retrieval and outfit matching"
```

**Does:** Commits only Phase 2E code; generated vectors remain ignored. **Success:** commit summary lists the Phase 2E files. **If it fails, send:** both commands and complete Git error/status output.

### 14. Push manually

**Command**

```powershell
git push origin main
```

**Does:** Pushes the validated commit. **Success:** remote reports the new commit on `main`. **If it fails, send:** command and complete Git output; do not force-push.

## If any runtime command fails

Send the command executed, last 30–50 terminal lines, traceback/error text, and the relevant generated/imported/test count. Never send `.env`, database URLs, keys, tokens, or credentials.

Expected final live counts: `products = 6018`, `product_embeddings = 6018`, and `embedded product rows = 6018`, all with dimension 384.
