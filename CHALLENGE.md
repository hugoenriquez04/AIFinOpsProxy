# AI FinOps Challenge - Specification

**Format:** University hackathon - two days  
**Deliverable:** A ten-minute live team demo

## Challenge

Companies increasingly use generative AI services from multiple providers,
but often lack visibility into who spends money, how much each request costs,
and whether that spending is justified.

Build an AI control layer that:

1. Transparently intercepts AI API calls.
2. Records the estimated cost of every request.
3. Applies per-consumer budget limits.
4. Recommends cost optimizations such as cheaper models, response caching,
   or token reduction.

## Requirements

| Requirement | Details |
| --- | --- |
| Multiple providers | Support at least two AI providers, such as Ollama and Groq or two Ollama containers. |
| Any stack | Teams may choose any language, framework, and database. |
| No production keys | Use sandbox accounts, free tiers, local models, or mocks. |
| Multiple consumers | Simulate at least two independent consumers with separate cost tracking. |

## Acceptance criteria

- The proxy intelligently routes requests between at least two providers.
- Token usage and cost are recorded for every request.
- At least two consumers have separate histories and spending totals.
- A configurable budget limit produces a visible block, alert, or degradation.
- At least two explicit cost-saving criteria are explained.
- The solution is demonstrated live.

## Evaluation areas

### Cost visibility

- Capture token usage for both providers.
- Break down cost by team, project, or consumer.
- Keep cost calculations consistent with provider pricing.

### Governance and budgets

- Configure limits per consumer or team.
- Trigger visible alerts when a threshold is crossed.
- Maintain an audit log of AI calls.
- Show a future-cost projection based on usage trends.

### Cost-saving decisions

- Define when a cheaper model should be selected.
- Explain the trade-off between cost and quality.
- Demonstrate the rules using real usage data.

### Architecture and security

- Keep the design provider-agnostic.
- Separate proxy, storage, and reporting responsibilities.
- Never expose API keys to consumers.

### Presentation

The demo should tell a clear story that a non-technical judge can follow.
