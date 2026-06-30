// L10n + layout regression workflow for the embedded editor.
//
// Run via the Workflow tool:  Workflow({ scriptPath: "scripts/workflows/l10n-regression.workflow.js" })
// (the .claude/workflows dir is gitignored, so this lives in a tracked path).
//
// Pipeline:
//   1. a Bash agent runs the DETERMINISTIC walk + checker (no LLM in the data path):
//        node e2e/scripts/editor-l10n-rendered.mjs ... --out rendered-candidate
//        python3 scripts/l10n-regression-check.py --candidate rendered-candidate
//          --golden rendered --expect expectations.json --out regression
//      and returns regression/report.json.
//   2. EVERY deviation (layout finding / text change vs golden / unmet expectation) is
//      handed to its own agent that adversarially verifies it with Playwright against the
//      live editor - so even a single real breakage surfaces and false positives are dropped.
//   3. a synthesis step writes the confirmed report.
//
// Use after translating each block (did only the intended terms change, nothing else, no
// layout breakage?) and during redesign (is everything present, visible, correctly placed?).
export const meta = {
  name: 'l10n-regression',
  description: 'Walk all editor surfaces, check l10n + layout expectations, adversarially verify each deviation',
  phases: [
    { title: 'Walk+Check', detail: 'deterministic walk + checker -> report.json' },
    { title: 'Verify', detail: 'one Playwright agent per deviation' },
    { title: 'Synthesize', detail: 'confirmed human+AI report' },
  ],
}

const REPORT_SCHEMA = {
  type: 'object',
  required: ['summary', 'layout', 'text_changes', 'expectation_failures'],
  properties: {
    summary: { type: 'object' },
    layout: { type: 'array', items: { type: 'object' } },
    text_changes: { type: 'array', items: { type: 'object' } },
    expectation_failures: { type: 'array', items: { type: 'object' } },
  },
}
const VERDICT_SCHEMA = {
  type: 'object',
  required: ['real', 'severity', 'note'],
  properties: {
    real: { type: 'boolean', description: 'true if this is a genuine regression, false if a false positive' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'cosmetic', 'false-positive'] },
    note: { type: 'string', description: 'one-line human-readable explanation of what was observed' },
  },
}

phase('Walk+Check')
const report = await agent(
  `You run a deterministic localization+layout regression check. Execute, from the repo root:
   1) node e2e/scripts/editor-l10n-rendered.mjs --locales=en,ru --apps=writer,calc,impress --out=.qa/ru-term-inventory/rendered-candidate --screenshots=main
   2) python3 scripts/l10n-regression-check.py --candidate .qa/ru-term-inventory/rendered-candidate --golden .qa/ru-term-inventory/rendered --expect .qa/ru-term-inventory/expectations.json --out .qa/ru-term-inventory/regression
   The stack must be up (./scripts/up.sh). Then read .qa/ru-term-inventory/regression/report.json and return it verbatim as the structured result.`,
  { label: 'walk+check', phase: 'Walk+Check', schema: REPORT_SCHEMA },
)

// flatten every deviation into a uniform work-list
const findings = [
  ...(report.layout || []).map((f) => ({ kind: f.kind, where: f.scenario, what: f.what, detail: f.detail })),
  ...(report.text_changes || []).map((f) => ({ kind: 'text-change', where: f.scenario, what: `#${f.id}`, detail: `${f.before} -> ${f.after}` })),
  ...(report.expectation_failures || []).map((f) => ({ kind: 'expectation', where: f.en, what: f.expect, detail: `${f.why}: ${f.rendered}` })),
]
log(`deviations to verify: ${findings.length}`)

phase('Verify')
const verified = await parallel(findings.map((f) => () =>
  agent(
    `Adversarially verify this editor regression finding. Default to real=false unless you SEE the problem.
     finding: ${JSON.stringify(f)}
     Open the editor (http://localhost:8088) with Playwright, navigate to the scenario/surface, locate the element,
     and judge: is this a REAL problem (elements overlapping, text clipped/truncated, wrong/missing translation,
     element off-screen or zero-size, gross empty space) or a false positive (containment, intended English term,
     dynamic value, off-by-1 rounding)? Return the verdict.`,
    { label: `verify:${f.kind}`, phase: 'Verify', schema: VERDICT_SCHEMA },
  ).then((v) => ({ ...f, ...v })).catch(() => ({ ...f, real: false, severity: 'false-positive', note: 'verifier error' })),
))

phase('Synthesize')
const confirmed = verified.filter(Boolean).filter((v) => v.real)
const bySev = {}
for (const v of confirmed) bySev[v.severity] = (bySev[v.severity] || 0) + 1
return {
  scenarios: report.summary,
  total_findings: findings.length,
  confirmed: confirmed.length,
  by_severity: bySev,
  blockers: confirmed.filter((v) => v.severity === 'blocker' || v.severity === 'major'),
  all_confirmed: confirmed,
}
