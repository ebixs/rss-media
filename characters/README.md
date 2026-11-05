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
