# AI docs review workflow (n8n)

When someone opens or updates a pull request in a docs repo, this n8n workflow sends each changed page to Claude for review. It then posts **one** comment on the pull request with a table of suggestions.

```
GitHub PR webhook → keep opened/updated PRs → list changed files → keep .md pages (max 10)
  → get each page → build review prompt → Claude review → format one comment → post on PR
```

## Why it's built this way

- **AI does only what a script can't.** The [docs checker](../README.md) already handles product names, filler words and GitBook syntax, so the prompt tells Claude not to repeat them. Claude looks only at missing steps, prerequisites, jargon and incomplete code.
- **Guarded against AI failure.** Pages are sent with line numbers, and every suggestion must point to a line. Claude must write "Check with engineering:" instead of inventing product behaviour, and "No issues" when a page is fine. Rows that don't fit the `LINE | problem | fix` format are dropped.
- **Low noise.** All suggestions go into one comment, not one per line. The comment says these are suggestions and that a writer decides.
- **Cost guard.** It reviews at most 10 pages per pull request.

## Set it up (about 30 minutes)

1. **Run n8n:** use n8n Cloud (free trial) or run it locally with `docker run -it --rm -p 5678:5678 n8nio/n8n`, then open http://localhost:5678.
2. **Import:** *Workflows → Import from file →* `ai-docs-review-workflow.json`.
3. **Create two credentials** (type *Header Auth*):
   - **GitHub token**: Name `Authorization`, Value `Bearer <a GitHub fine-grained token with Pull requests: read & write and Contents: read on your repo>`
   - **Anthropic API key**: Name `x-api-key`, Value `<your Anthropic API key>`
   Open each HTTP Request node and select the matching credential.
4. **Connect GitHub:** in your repo, go to *Settings → Webhooks → Add webhook*. Payload URL: the **Production URL** shown on the webhook node (for a local n8n, expose it with a tunnel such as ngrok). Content type: `application/json`. Events: *Pull requests*.
5. **Activate** the workflow, open a pull request that changes a `.md` file (for example `examples/install-apim-helm.md`), and check the comment that appears.

## Status

Built and the JSON checked. **Not yet run end to end in n8n.** Test it, fix anything that breaks, then add a screenshot of a real PR comment here.

## Next idea: release-notes drafts

When a release is tagged, the workflow collects the merged pull requests, Claude drafts release notes grouped into *New*, *Improved* and *Fixed*, and a writer reviews them before publishing. AI does the first draft and a human owns the final version.
