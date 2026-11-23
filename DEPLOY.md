# Deploy BazaarCart

Use the existing public GitHub repository `FatikImran/bazaar-cart`, **Neon Postgres** for durable memory, **Render** for the Dockerized API, and **Vercel** for the storefront. Render is the recommended API host because it can deploy the Dockerfile directly from the project repository and provides a separate public URL for the grader.

## 1. Publish the project source

Push the contents of the local `BazaarCart` folder to the GitHub repository root. Include `app`, `web`, tests, and deployment files. Keep the cloned `Workshop` repository, personal workshop materials, and credentials outside this public repo.

Suggested commit message: `Build BazaarCart storefront and LangGraph sales agent`.

## 2. Create the Neon database

1. In Neon, create a project and copy the **direct** Postgres connection string from the Connect dialog. Keep SSL enabled in that string.
2. Set it as `DATABASE_URL` in Render. Startup creates the application and LangGraph checkpoint tables and seeds the demo store. No manual SQL is required.
3. Keep the Neon project active through evaluation and verify that the deployed API can read `/catalog`.

## 3. Deploy the Render API

1. Create a new Web Service, select `FatikImran/bazaar-cart`, select Docker and the free instance, and leave the build context at the repo root.
2. Set the health check path to `/health`. Add these service environment variables through Render:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon direct connection string |
   | `ANTHROPIC_API_KEY` | Your group's key from the instructor |
   | `ANTHROPIC_MODEL` | `claude-haiku-5-5` |
   | `SELLER_TOKENS_JSON` | JSON object mapping store slugs to private tokens, e.g. `{"demo":"REPLACE_WITH_RANDOM_TOKEN"}` |
   | `DAILY_MODEL_CALL_LIMIT` | Start at `100` and adjust based on real usage and grading needs |
   | `FRONTEND_ORIGINS` | Optional, exact Vercel origin if using direct cross-origin requests |

   Generate a seller token with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and paste it directly into the Render dashboard. Tokens for additional store slugs should be distinct.
3. Deploy and open `/health` and `/catalog` on the Render URL. Confirm that `/health` returns plain `ok` and the catalog contains the seeded products.
4. Call `POST /chat` once to verify that the instructor's key can access the required model. If the model is rejected, verify the exact model identifier with the instructor.
5. Run `python benchmark.py https://YOUR-RENDER-HOST` from the repo root. The successful checkout creates one demo order and decrements stock by one. Run on the demo store and retain the actual results for the README.

## 4. Deploy the Vercel frontend

1. Copy `web/vercel.example.json` to `web/vercel.json`. In the copy, replace `REPLACE-WITH-YOUR-RENDER-HOST` with your Render hostname. Commit the copy, which contains only a public URL.
2. Import the GitHub repo into Vercel. Select **Other** for the framework and `web` as the root directory. Use the Hobby plan and leave the build command empty.
3. Open the public URL, check the catalog, and try the shopping assistant. Open **Seller dashboard** and paste the seller token from Render. Upload `docs/catalog-example.csv` if you want to demonstrate catalog import.
4. Check both the Vercel URL and the direct API immediately before submission and through the evaluation window. Free Render services can cold-start.

## 5. Finish the submission

- Record a 2-3 minute demo covering catalog upload, product search, checkout confirmation, the dashboard, and cross-thread preference recall. Share an unlisted video or a Drive link viewable by anyone with the link. Add a GIF of the actual flow to the README.
- Update the benchmark table with deployed results, token counts, and the five instructor attack cases when supplied. Capture configured storefront and dashboard screenshots.
- Upload the completed canvas photo and share it as viewable by anyone with the link.
- The group leader submits the form and sends the same links in Google Classroom.
- For the paper handout's bonus, ask a real small seller to try the site and record actual feedback with their permission.
