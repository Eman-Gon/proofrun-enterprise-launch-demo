# Customer import compatibility

Northstar imports synthetic customer records. Identifiers are opaque strings:
every accepted identifier must be returned exactly as provided. Numeric-looking
IDs, IDs with leading zeros, and partner IDs with letters and punctuation are
valid. IDs must never be interpreted as numbers.

`POST /customers/import` accepts a JSON object with `customer_id` and `name`.
Both are nonempty strings. Valid requests return HTTP 201 with
`{"customer": {"customer_id": "...", "name": "..."}, "imported": true}`.
Invalid records return HTTP 422 with `{"error": "invalid_customer"}`.
This existing endpoint's response status and body must remain compatible.

The new CSV preview feature is additive. It validates records and identifies
duplicate customer IDs before import. It must preserve identifiers, and it must
not change the existing single-record import contract. It does not persist data.

`POST /imports/preview` is available in version 1.1. It accepts a JSON object with
a `csv` string. Required CSV headers are `customer_id,name`; at most 100 data rows
are accepted. A preview reports total, ready, and rejected counts and a status
for each row. Row numbers correspond to CSV records with the header as row 1.

`GET /health` reports availability. `GET /version` reports the release label and
feature flags. `GET /` serves the browser demo. A health check alone says nothing
about release compatibility. All data in this project is fictional.
