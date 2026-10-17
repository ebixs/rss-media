# Persian adaptation of instagram-agent-skill

Upstream: https://github.com/Jakeschincariol/instagram-agent-skill (MIT, see `LICENSE`, commit in `UPSTREAM`).
`skills/*/SKILL.md` are unchanged. Only the tools were changed, so they work on Persian text:

- **ig-human/slop.json**
  - U+200C (ZWNJ, نیم‌فاصله) removed from the "delete" list. Persian spelling needs it; upstream would turn «می‌خواهد» into «میخواهد».
  - Added Persian slop words and phrases (family `fa-words` / `fa-phrases`).
  - Added Persian structural tells: «نه تنها…بلکه», banned claims (بهترین/تضمینی/۲۴ ساعته), rhetorical one-word questions, greeting openers.
- **ig-human/humanize.py**
  - ZWNJ is exempt from the catch-all format-character deletion.
  - «؟» and «،» are handled as punctuation.
- **ig-human/detect.py**
  - Persian letters count as words.
  - Persian pronouns and common colloquial forms count toward VOICE.
  - ZWNJ is not counted as a fingerprint.
  - VOICE is still English-calibrated, so for Persian treat it as a guide only.
- **ig-caption/caption.py**
  - Persian hashtags (with ZWNJ) are counted.
  - Persian calls to action are recognised (call / save / DM / comment keyword / share).
  - Persian concrete markers and .ir/.me links are recognised.
- **ig-reel/hookscore.py**
  - Persian tokens are recognised.
  - Persian numbers, stakes words, weak openers, imperatives and address forms are recognised.
  - The greeting dealbreaker includes «سلام/درود».

Tested 2026-10-17 on the published burn-dressing caption: ZWNJ count unchanged (4 → 4). Hooks rank sensibly; the greeting hook is flagged with a dealbreaker.
