# Brand characters (owner's choice, 2026-11-05)

3D animated-film style. Every scene that shows a character sends its reference image
(characters/ref/<name>.jpg) to FLUX.2 klein so the character stays the same.

| name in post.md | Persian | reference | how to describe it in a prompt |
|---|---|---|---|
| mahtab | مهتاب | ref/mahtab.jpg | young Iranian female home-care nurse, light-grey loosely draped hijab, navy nurse uniform with mint trim, silver stethoscope, navy medical bag |
| ebrahim | ابراهیم | ref/ebrahim.jpg | young Iranian male nurse, short dark hair, short trimmed beard, navy nurse uniform with mint trim, silver stethoscope, tablet |
| khonejan | خونه‌جان | ref/khonejan.jpg | friendly cartoon house mascot: navy roof, ivory walls, mint square window-eyes, wooden arched door, white gloves, silver stethoscope, red heart balloon |

In post.md a reel scene names its characters with `characters_<n>: mahtab, khonejan`
(up to 4). In image_prompt_<n> refer to them as "the nurse from image 0",
"the house character from image 1", in the same order.
Rules: no text in images; never a real patient; medical scenes stay safe (no needles shown).

## Available poses (characters/cut)
- mahtab: waving with one hand, medical bag in the other
- mahtab-walk: standing with the medical bag, waving (use for walk-in entrances)
- mahtab-phone: smiling, talking on a mobile phone held to her ear (booking / call scenes)
- ebrahim: standing, holding a tablet to his chest
- ebrahim-thumbsup: smiling, thumbs up, tablet in the other hand (approval / "done")
- mahtab-explain: smiling, one open palm raised to the side, no bag (explaining / offering info)
- ebrahim-explain: calm, both open hands in front of chest, tablet under arm (explaining)
- khonejan: waving, heart balloon, stethoscope, wooden door (re-cut 2026-11-07: chimney and balloon string now complete; old cut in cut/archive)
- khonejan-worried: worried, gloved hands on its cheeks, no balloon (problem / opening scenes; use with "mood": "worried")

Older versions of replaced cut-outs live in characters/cut/archive (not used by the reels).
Quality notes per run: characters/quality-log.md.

New poses come from characters/pose-backlog.json (scheduled task, Thursdays and Saturdays).
