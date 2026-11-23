# Gravitee docs toolkit

A docs-as-code portfolio built around Gravitee-style documentation (GitBook Markdown):

| Part | What it is | Status |
|---|---|---|
| [`checker/`](checker/check.py) + [`rules.yaml`](rules.yaml) | Rule-based docs checker with an optional Claude review | Working, tested on sample pages |
| [`styles/Gravitee`](styles/Gravitee) | The same house rules as a Vale style | Written, not yet run in Vale |
| [`.github/workflows`](.github/workflows/docs-check.yml) | Runs the checker, Vale and AI review on every pull request | Written, not yet run on GitHub |
| [`n8n/`](n8n/README.md) | AI-assisted review workflow: PR → Claude → one review comment on the PR | Logic tested with sample data; not yet run in n8n |
| [`guides/`](guides/) | Two how-to guides: [install Gravitee on Kubernetes with Helm](guides/install-gravitee-on-kubernetes-with-helm.md) and [expose Kafka events through Gravitee](guides/expose-kafka-events-with-gravitee.md). Both pass the checker. | Drafted from Gravitee's official docs; being tested hands-on |

The guides are real content, the checker keeps them consistent, and n8n automates the review.

---

## Docs checker

A docs-as-code quality check that runs on every pull request and catches problems before a reviewer has to.

## Why

Docs reviews spend a lot of time on the same small issues: product names written three ways, unclosed `{% hint %}` blocks that break the page, images with no alt text, "click here" links. A script catches these in seconds. Human reviewers can then focus on what matters: is the page correct, complete and clear?

## How it works

It works in two layers:

| Layer | What it checks | Cost | Fails the build? |
|---|---|---|---|
| **Rule checks** | Product names (Gravitee, API Management, Developer Portal, Gateway…), filler words ("simply", "just", "easy"), "click on" → "select", GitBook block syntax (`hint`, `tabs`, `code`, `stepper` opened and closed, valid hint styles), sentence-case headings, sentence length, alt text, code-block languages, vague link text | Free, instant | Only for broken GitBook syntax |
| **AI review** (optional) | Judgement calls a regex can't make: missing or out-of-order steps, prerequisites, unexplained jargon, pages mixing tutorial/how-to/reference (Diátaxis), incomplete code samples | One API call per page | Never – suggestions only |

The AI layer is built to be careful:
- It's told what the rule layer already covers, so it doesn't repeat it.
- It must cite a line number and a concrete fix for each issue.
- It must say "Check with engineering" instead of guessing product behaviour.
- Its output shows as *notices*, so a writer always makes the final call.

All rules live in [`rules.yaml`](rules.yaml), so writers can change them without touching code.

### Vale

The same house rules are also written as a [Vale](https://vale.sh) style in [`styles/Gravitee`](styles/Gravitee): product names, filler words, "select" not "click on", sentence-case headings and sentence length. `.vale.ini` tells Vale to skip GitBook `{% %}` tags. Teams that already use Vale can drop these rules straight in. The Python checker covers what Vale can't do well: checking that GitBook blocks are opened and closed, and the AI review.

```bash
vale examples/
```

*Vale rules: written and YAML-validated, but not yet run against Vale itself. That's next on the list.*

## Run it

```bash
pip install pyyaml anthropic
python checker/check.py examples/                  # rule checks
python checker/check.py examples/ --ai             # + AI review (set ANTHROPIC_API_KEY)
python checker/check.py docs/ --format github      # GitHub Actions annotations
```

Example output on [`examples/install-apim-helm.md`](examples/install-apim-helm.md), a deliberately flawed page:

```text
install-apim-helm.md:5   [warning] heading-case: Use sentence case in headings (lowercase: On, Using).
install-apim-helm.md:7   [warning] product-name: Use 'Kubernetes', not 'kubernetes'.
install-apim-helm.md:7   [warning] word-choice: Remove 'simply' – it can make readers feel slow...
install-apim-helm.md:9   [error]   gitbook-hint: Unknown hint style 'note'. Use one of: danger, info, success, warning.
install-apim-helm.md:22  [warning] code-language: Add a language to this code block...
install-apim-helm.md:31  [error]   gitbook-block: '{% tabs %}' is never closed with '{% endtabs %}'.
...
1 file(s) checked: 2 error(s), 15 warning(s), 0 AI suggestion(s).
```

## In CI

[`.github/workflows/docs-check.yml`](.github/workflows/docs-check.yml) checks only the Markdown files changed in a pull request, and shows the results inline on the PR. The AI step runs only if the repository has an `ANTHROPIC_API_KEY` secret.

## Where the rules come from

- **Confirmed** from Gravitee's public docs (Nov 2026): GitBook block syntax (`{% hint style="info" %}`, `{% tabs %}`, `{% code %}`), product names as written in page titles, and the fork → branch → pull request contribution flow.
- **Assumed** from common developer-docs practice (Google and Microsoft style guides): word choice, sentence case, sentence length, alt text, link text. Gravitee's own "Style Guide and Best Practices" page wasn't online when I built this, so these are defaults to adjust to the team's real guide.

## Next steps

- [ ] Check relative links and image paths exist
- [ ] Flag passive voice in procedure steps
- [ ] Turn AI suggestions into a single PR comment instead of line notices
- [ ] Add tests for each rule
