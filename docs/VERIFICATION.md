# Verification report

| Check | Actual observation |
|---|---|
| Python contract suite | 6 tests passed. |
| Running HTTP preview | `GET /api/health` returned HTTP 200 with the exact body `ok`. |
| Browser preview | Edge rendered the storefront and seller access screen from the running preview. PNGs are in this folder. |
| JavaScript | `node --check web/app.js` exited successfully. |
| Database and Anthropic integration | Pending the Neon connection string and instructor-issued Claude key on the hosted API. |
| Hidden benchmark, spend and live latency | Pending the deployed run. |

The local suite covers the grading health endpoint, invalid chat input, unknown grading fields, seller authorization, negative stock validation, and the LangGraph guard against confirmation without a pending checkout.

## Live verification to record

After deploying, run the included benchmark against the direct API and record the pass rate and token totals. Test uploading valid and invalid CSVs, updating stock, recovering preferences after an API restart, checking that a different user or seller cannot read the records, and confirming that a retry does not decrement stock twice. Capture the storefront after the catalog loads and a seller dashboard with a completed test order.
