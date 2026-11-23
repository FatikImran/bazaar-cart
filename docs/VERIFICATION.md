# Verification report

| Check | Actual observation |
|---|---|
| Python contract suite | 6 tests passed. |
| Running HTTP preview | `GET /api/health` returned HTTP 200 with the exact body `ok`. |
| Browser preview | Edge rendered the storefront and seller access screen from the running preview. PNGs are in this folder. |
| JavaScript | `node --check web/app.js` exited successfully. |
| Database and Anthropic integration | Railway returned the seeded Neon catalog and successfully answered a chat request using Claude. |
| Live project benchmark | 15/15 passed on November 23, 2026. |
| Live per-request elapsed time | 1.02–4.48 seconds across 15 cases. |
| Live model tokens | 3,695 input and 227 output across 15 cases. |

The local suite covers the grading health endpoint, invalid chat input, unknown grading fields, seller authorization, negative stock validation, and the LangGraph guard against confirmation without a pending checkout.

## Live verification to record

The live run covered search, cart memory, cross-thread preferences, user isolation, checkout, duplicate confirmation, and five project-authored safety tests. The hidden instructor benchmark, preference recovery after an API restart, and the deployed Vercel UI are still to be verified.
