# Applicant profile stage

Schema 1.0.0 and workflow 1.1.0 provide the evidence-linked export contract and a working local, agent-assisted text extraction, clarification, review, revision and approval workflow. The private pilot remains separately human-gated.

- [Integration, evidence and lifecycle contract](docs/profile-contract.md)
- [Privacy and replaceable local storage contract](docs/privacy.md)
- [JSON Schema](schemas/applicant-profile-1.0.0.schema.json)
- [Synthetic review](examples/review.md)
- [Grouped review and evidence-range example](examples/evidence-review/README.md)
- Synthetic exports in `examples/`: two distinct backgrounds, uncertainty, conflicting evidence, clarification and a revised frozen example.

Run from the repository root:

```sh
python3 grad-compass-research-engine/scripts/validate.py
```

No network, package installation, private input or credentials are needed. The validator implements the exact JSON Schema keyword subset used by this contract and semantic reference checks. A general Draft 2020-12 validator can also consume the schema; cross-reference and approval semantics additionally require the supplied validator. Synthetic approvals are test records, never human approval of an actual applicant.

- [Working workflow, CLI, supported formats and approval procedure](docs/workflow.md)
- [Reusable extraction prompt](prompts/extract.md)
- Focused integration checks: `python3 -m unittest discover -s grad-compass-research-engine/tests -v` (uses Paperclip run scratch).
