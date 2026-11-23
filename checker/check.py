#!/usr/bin/env python3
"""Gravitee docs checker.

Two layers:
1. Rule checks (fast, free, deterministic): product names, filler words, GitBook
   block syntax, heading case, sentence length, image alt text, code-block language.
2. Optional AI review (--ai): sends the page plus the rule set to Claude and asks for
   judgement calls a regex can't make (missing steps, unclear prerequisites, etc.).
   AI findings are suggestions for a human writer to verify, never auto-applied.

Usage:
    python checker/check.py docs/                 # rule checks on every .md file
    python checker/check.py page.md --ai          # add an AI review (needs ANTHROPIC_API_KEY)
    python checker/check.py docs/ --format github # GitHub Actions annotations
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = ROOT / "rules.yaml"


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    message: str
    level: str = "warning"  # "error" for broken syntax, "warning" for style, "notice" for AI


# ---------------------------------------------------------------- helpers

def prose_lines(text: str):
    """Yield (line_no, line) for prose only: skips front matter, fenced code and inline code."""
    in_fence = False
    in_front = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if i == 1 and stripped == "---":
            in_front = True
            continue
        if in_front:
            if stripped == "---":
                in_front = False
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # drop inline code, URLs, link targets and GitBook tags so we only lint words
        cleaned = re.sub(r"`[^`]*`", "", line)
        cleaned = re.sub(r"\]\([^)]*\)", "]", cleaned)
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        cleaned = re.sub(r"{%.*?%}", "", cleaned)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        yield i, cleaned


# ---------------------------------------------------------------- rule checks

def check_product_names(path, text, rules):
    out = []
    for i, line in prose_lines(text):
        for correct, wrongs in rules.get("product_names", {}).items():
            for wrong in wrongs:
                for m in re.finditer(rf"(?<![\w/.-]){re.escape(wrong)}(?![\w/.-])", line):
                    # "gateway" at the start of a sentence etc. is still worth a look,
                    # but skip it when it's part of the correct form (e.g. "API Gateway")
                    if correct in line[max(0, m.start() - 15): m.end() + 15] and wrong.lower() == correct.lower():
                        continue
                    out.append(Finding(path, i, "product-name",
                                       f"Use '{correct}', not '{wrong}'."))
    return out


def check_avoid_words(path, text, rules):
    out = []
    for i, line in prose_lines(text):
        for word, advice in rules.get("avoid_words", {}).items():
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", line, flags=re.IGNORECASE):
                out.append(Finding(path, i, "word-choice", advice))
    return out


def check_gitbook_blocks(path, text, rules):
    """Every {% hint %}, {% tabs %} etc. must be closed, and hint styles must be valid."""
    out = []
    cfg = rules.get("gitbook", {})
    pairs = cfg.get("paired_tags", {})
    closers = {v: k for k, v in pairs.items()}
    allowed = set(cfg.get("allowed_hint_styles", []))
    stack: list[tuple[str, int]] = []
    in_fence = False
    for i, raw in enumerate(text.splitlines(), start=1):
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`]*`", "", raw)  # tags quoted as inline code aren't real blocks
        for tag in re.finditer(r"{%\s*(\w+)([^%]*)%}", line):
            name, args = tag.group(1), tag.group(2)
            if name in pairs:
                stack.append((name, i))
                if name == "hint":
                    style = re.search(r'style="([^"]+)"', args)
                    if not style:
                        out.append(Finding(path, i, "gitbook-hint", "Hint has no style – add style=\"info\" (or success/warning/danger).", "error"))
                    elif style.group(1) not in allowed:
                        out.append(Finding(path, i, "gitbook-hint",
                                           f"Unknown hint style '{style.group(1)}'. Use one of: {', '.join(sorted(allowed))}.", "error"))
            elif name in closers:
                opener = closers[name]
                if not stack or stack[-1][0] != opener:
                    out.append(Finding(path, i, "gitbook-block", f"'{{% {name} %}}' has no matching '{{% {opener} %}}'.", "error"))
                else:
                    stack.pop()
    for name, line_no in stack:
        out.append(Finding(path, line_no, "gitbook-block", f"'{{% {name} %}}' is never closed with '{{% {pairs[name]} %}}'.", "error"))
    return out


def check_headings(path, text, rules):
    out = []
    cfg = rules.get("headings", {})
    keep = set(cfg.get("keep_caps", []))
    max_words = rules.get("limits", {}).get("max_heading_words", 10)
    for i, line in prose_lines(text):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if not m:
            continue
        heading = m.group(2).strip().rstrip("#").strip()
        words = re.findall(r"[A-Za-z][\w'-]*", heading)
        if len(words) > max_words:
            out.append(Finding(path, i, "heading-length", f"Heading has {len(words)} words – keep it under {max_words}."))
        if cfg.get("sentence_case") and len(words) > 1:
            # A capital straight after a colon starts a new phrase ("Part 1: Run Kafka"), so allow it.
            after_colon = {m.group(1) for m in re.finditer(r":\s*([A-Za-z][\w'-]*)", heading)}
            title_cased = [w for w in words[1:] if w[0].isupper() and w not in keep
                           and w not in after_colon and not w.isupper()]
            if title_cased:
                out.append(Finding(path, i, "heading-case",
                                   f"Use sentence case in headings (lowercase: {', '.join(title_cased)})."))
        if heading.endswith((".", ":")):
            out.append(Finding(path, i, "heading-punctuation", "Don't end a heading with a full stop or colon."))
    return out


def check_sentence_length(path, text, rules):
    out = []
    limit = rules.get("limits", {}).get("max_sentence_words", 30)
    for i, line in prose_lines(text):
        if line.lstrip().startswith(("#", "|", ">")):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            n = len(re.findall(r"\b\w+\b", sentence))
            if n > limit:
                out.append(Finding(path, i, "sentence-length", f"Sentence has {n} words – try to split it (limit {limit})."))
    return out


def check_images_and_code(path, text, rules):
    out = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence and stripped == "```":
                out.append(Finding(path, i, "code-language", "Add a language to this code block (for example ```bash or ```yaml) so it highlights correctly."))
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            if not m.group(1).strip():
                out.append(Finding(path, i, "image-alt", "Image has no alt text – describe what it shows for screen-reader users."))
        for m in re.finditer(r"<img\b[^>]*>", line):
            if not re.search(r'alt="[^"]+"', m.group(0)):
                out.append(Finding(path, i, "image-alt", "Image has no alt text – describe what it shows for screen-reader users."))
        for m in re.finditer(r"\[(here|click here|this link|link)\]\(", line, flags=re.IGNORECASE):
            out.append(Finding(path, i, "link-text", f"Link text '{m.group(1)}' says nothing out of context – name the destination instead."))
    return out


RULE_CHECKS = [
    check_gitbook_blocks,
    check_product_names,
    check_avoid_words,
    check_headings,
    check_sentence_length,
    check_images_and_code,
]


# ---------------------------------------------------------------- AI review

AI_PROMPT = """You are reviewing one page of Gravitee's product documentation (GitBook Markdown).
A rule-based linter has already checked spelling of product names, filler words and syntax,
so do NOT repeat those. Focus only on judgement calls:

{focus}

Rules:
- Only report real problems you can point to. If the page is fine, say "No issues."
- For each issue give: the line number, a one-sentence problem, and a concrete fix.
- Never invent product behaviour. If you are unsure whether a step is correct, say
  "Check with engineering:" rather than guessing.
- Output one issue per line in the form:  LINE | problem | suggested fix

Page ({name}), with line numbers:
{page}
"""


def ai_review(path: str, text: str, rules: dict) -> list[Finding]:
    try:
        import anthropic
    except ImportError:
        print("AI review skipped: run `pip install anthropic` first.", file=sys.stderr)
        return []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("AI review skipped: set ANTHROPIC_API_KEY.", file=sys.stderr)
        return []
    cfg = rules.get("ai_review", {})
    numbered = "\n".join(f"{n:>4}  {l}" for n, l in enumerate(text.splitlines(), start=1))
    prompt = AI_PROMPT.format(
        focus="\n".join(f"- {f}" for f in cfg.get("focus", [])),
        name=Path(path).name,
        page=numbered,
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=cfg.get("model", "claude-sonnet-4-5"),
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    reply = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    out = []
    for row in reply.splitlines():
        parts = [p.strip() for p in row.split("|")]
        if len(parts) >= 3 and parts[0].isdigit():
            out.append(Finding(path, int(parts[0]), "ai-review", f"{parts[1]} Suggested fix: {parts[2]}", "notice"))
    return out


# ---------------------------------------------------------------- CLI

def collect_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.suffix == ".md":
            files.append(p)
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check Gravitee docs pages against the style rules.")
    ap.add_argument("targets", nargs="+", help="Markdown files or folders")
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    ap.add_argument("--ai", action="store_true", help="Add an AI review (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--format", choices=["text", "github"], default="text")
    args = ap.parse_args(argv)

    rules = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8"))
    files = collect_files(args.targets)
    if not files:
        print("No .md files found.")
        return 0

    findings: list[Finding] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        for check in RULE_CHECKS:
            findings.extend(check(str(f), text, rules))
        if args.ai or rules.get("ai_review", {}).get("enabled_by_default"):
            findings.extend(ai_review(str(f), text, rules))

    findings.sort(key=lambda x: (x.file, x.line))
    for fd in findings:
        if args.format == "github":
            print(f"::{fd.level} file={fd.file},line={fd.line},title={fd.rule}::{fd.message}")
        else:
            print(f"{fd.file}:{fd.line}  [{fd.level}] {fd.rule}: {fd.message}")

    errors = sum(1 for x in findings if x.level == "error")
    warnings = sum(1 for x in findings if x.level == "warning")
    notices = sum(1 for x in findings if x.level == "notice")
    print(f"\n{len(files)} file(s) checked: {errors} error(s), {warnings} warning(s), {notices} AI suggestion(s).")
    # Only broken syntax fails the build; style issues are warnings for the writer to judge.
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
