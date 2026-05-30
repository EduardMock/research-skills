# paper-fetch-smiles log — Zhang 2024 Inorganics

## REVIEW — needs human attention

## VERIFIED — reviewer-confirmed
- caption-anchored cropper: 8/8 Figure crops PASS vs figs_truth/gt_1-8.png (parallel verifier subagents, 2026-05-29). Failure modes from first round (left-edge clip on Figs 1,3,4,5,8; bottom bleed on Fig 6) fixed by (a) widening x to 5%-margin page-content area, (b) trimming caption block yMax to last-line yMax + clipping to next-block yMin.  _(scripts/caption_crop.py)_
