# Reusable academic CV workflow

`build.py` reads one immutable frozen profile, its matching human approval receipt, and its `COMPLETE` marker. It verifies source identity and SHA-256 before rendering a master CV, research CV, and concise two-page CV. One private selection file controls wording, claim references, and variant selection. Each factual span must cite an approved profile subject and field; the builder records resolved claim IDs in a private claim audit. The public renderer contains no real applicant facts.

Run from the subproject root:

```sh
python3 cv/build.py --frozen private/frozen/REVISION --selection private/cv/selection.json --out private/cv/build
```

The command requires `pdflatex` and `pdfinfo`. Inspect all rendered pages before review handoff. The real concise CV build fails unless it is exactly two pages.

The renderer uses the MIT-licensed [CleanCV](https://github.com/giladturok/CleanCV) style retained under `cv/vendor/cleancv/`, with a restrained RenderCV-inspired visual adaptation: Source Sans Pro, navy section rules, aligned dates, compact contact icons, and title-first publication entries. It copies the style and license beside each editable LaTeX output, so the source can be rebuilt privately without network access. Applicant-specific wording and variant selection live only in the private claim-linked selection file. Contact icons are inferred from approved link values; the renderer does not add contact channels.

The public synthetic fixture exercises the same renderer with a different applicant background:

```sh
python3 cv/build.py --synthetic --frozen cv/synthetic/frozen --selection cv/synthetic/selection.json --out cv/synthetic/build
```

Private source inputs, selections, rendered files, manifests, and audits remain under Git-excluded `private/`. Synthetic build output is also Git-excluded. A new approved profile revision requires rebuilding and reviewing every affected variant.
