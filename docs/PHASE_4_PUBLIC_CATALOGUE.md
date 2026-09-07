# Phase 4 public catalogue

NexGen exposes a read-only product browsing surface at `/v1/catalogue`. Browser clients use `VITE_BACKEND_API_URL` and do not send Tool Gateway credentials.

## Endpoints

- `GET /v1/catalogue/products` supports `q`, `category`, `department`, `color`, `min_price`, `max_price`, `sort`, `limit`, `offset`, and `available_only`.
- `GET /v1/catalogue/products/{product_id}` returns one public product projection.
- `GET /v1/catalogue/facets` returns current catalogue filter values and price bounds.
- `GET /v1/catalogue/styled-edit` returns current image-backed products for editorial presentation.

The list limit defaults to 24 and cannot exceed 60. Responses expose product content, public availability, and catalogue media only. Customer, order, database, audit, and credential fields are excluded by response schemas. Tool Gateway endpoints under `/v1/tools` retain `X-Tool-Secret` authentication.

## Runtime configuration

The backend reads the catalogue through PostgreSQL using `SUPABASE_DB_URL`. The frontend requires only `VITE_BACKEND_API_URL`. `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are not required for this database-backed public catalogue path.

Product media contracts use `image_urls` today. The frontend product model reserves optional `videoUrl`, `modelWalkUrl`, `lookbookMedia`, and `variantMedia` fields for future catalogue-owned media.
