# Character pose quality log

One line per scheduled pose run (Thursdays and Saturdays). Run count drives the quality pass (every 4th run).

- 2026-11-07 · run 1 · made khonejan-worried (seed 892), mahtab-phone (753), ebrahim-thumbsup (761); all three renders passed (identity, pose, hands) but the bot cut-outs failed (khonejan: gable wall and chimney cut away; ebrahim: backdrop patch between arm and body; mahtab: invisible fringe widening the frame). Fixed without new renders: scripts/cutouts.py now tests colour against a fitted background model (adds missed ivory parts, keeps backdrop-coloured gaps and floor shadow out); all three re-cut and passed. Replaced khonejan.png with a re-cut of its own render c-house-23 (chimney + balloon string complete; same image, so identity unchanged); old file in cut/archive/khonejan-2026-11-07.png. Parked the never-rendered bg-street/bg-door plate jobs in characters/jobs-parked.json so a push renders only this run's 3. Failed: none. Backlog left: 9.
