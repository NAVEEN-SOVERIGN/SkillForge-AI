# SkillForge Code Context — Hackathon Submission

## Project title

**SkillForge Code Context: Why The Code Is Like This**

## One-line pitch

**Ask why a codebase works the way it does, then follow the answer through the decisions, discussions, people, and files that support it.**

## Problem

Software teams preserve source code more reliably than the reasoning behind it. The reason a retry limit exists, a service was not migrated, or a compatibility flag must remain enabled may be scattered across old pull requests, issues, commits, and design notes. Search finds matching words but cannot distinguish a governing decision from a later reversal. When experienced engineers leave, that context leaves with them.

## Solution statement

SkillForge Code Context turns a public repository’s history into an evidence trail for engineering decisions. A developer connects a GitHub repository and asks a plain-language “why” question. The system retrieves recent commits, pull requests, issues, and likely architecture decision records, ranks the evidence, and returns a concise answer with direct source links. A relationship view connects records to contributors, source types, and changed files. When configured, Neo4j AuraDB persists the repository evidence graph; Gemini can synthesize a response from retrieved records, with an evidence-only fallback when the model is unavailable. If no source establishes the rationale, the product says that the answer is unknown. Possible reversals are called out for human review rather than treated as confirmed supersession.

The distinctive idea is **decision provenance**: the answer is useful because a developer can inspect where it came from, who was involved, what code changed, and how strong the evidence is. Code Context is also a SkillForge learning tool: developers can study real engineering trade-offs and explain those decisions in portfolio projects.

## Differentiation

- **Decision history over document similarity:** answers surface repository events and relationships, not just paragraphs with similar words.
- **Citation-bound synthesis:** source IDs returned by Gemini are validated against the retrieved evidence set; every answer exposes its source links.
- **Honest uncertainty:** absence of explicit rationale produces a low-confidence investigation lead or an abstention.
- **Reversal awareness:** language indicating a revert or replacement is flagged as a possible supersession for review.
- **Useful graph connections:** repositories, evidence, people, and changed code paths are modeled as connected entities, with optional AuraDB persistence.
- **Low-friction first run:** the public demo works without sign-up or GitHub credentials.

## Current implementation and honest limits

The current MVP reads up to 100 recent commits, pull requests, and issues plus the recursive repository tree; fetches up to three likely ADR/design documents; and asks GitHub for changed files on the top three matching pull requests. Evidence ranking is deterministic lexical matching. Gemini is optional and runs server-side. A deterministic fallback quotes explicit rationale language or says the indexed sources do not establish a reason. The relationship graph is interactive in the browser; when AuraDB Query API credentials are configured, records can be persisted there.

This version does not yet index complete history, identify functions/configuration keys from source code, ingest incidents, authenticate private GitHub repositories, or calibrate confidence statistically. Supersession flags are heuristic signals, not proof that a decision is obsolete. The current Neo4j connection is optional and must be configured with server environment variables; do not claim live AuraDB persistence in a presentation unless those credentials are set and the sync is demonstrated.

## Suggested live demonstration

1. Open the homepage and choose **Try a repository** without signing in.
2. Connect a public repository with a meaningful commit and pull request history.
3. Ask a concrete question that names a behavior or file.
4. Show the answer, confidence label, and direct source cards; open one cited pull request.
5. Switch to the relationship graph and show the links among changed files, evidence, source types, and contributors.
6. Ask a question with no matching rationale and show the abstention behavior.
7. If AuraDB is configured, save the graph and show the persisted repository graph in Neo4j Browser.

## Technical stack

- React, TypeScript, and Vite frontend
- Express and Node.js backend
- GitHub REST API for public repository history
- Optional Google Gemini API for source-constrained answer synthesis
- Deterministic evidence-only fallback and source-ID validation
- Optional Neo4j AuraDB Query API for graph persistence

## Next build sprint milestones

1. Replace lexical ranking with hybrid semantic retrieval while keeping graph traversal in the answer path.
2. Parse source diffs to connect decisions to exact symbols and configuration keys.
3. Use explicit decision extraction with source spans and confidence calibration.
4. Detect supersession from linked changed files, chronology, and explicit reversal language.
5. Add complete-history ingestion, incremental refresh, and private-repository OAuth.
6. Add incident integrations and question-level feedback to improve retrieval quality.
