# Bullet Hell Candidate Prompt Contract

Return one JSON object with:

```json
{
  "structured_goal": {},
  "candidate_config": {}
}
```

`candidate_config` must be a complete Bullet Hell contract version `1.0`.
Preserve unspecified baseline fields. Do not add fields, code, comments, or Markdown.
Allowed pattern types are `ring`, `aimed_fan`, `spiral`, and `petal`.
The candidate is only a proposal and must pass deterministic validation before Unity can run.
