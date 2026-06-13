---
name: buildinpublic
description: Turn recent git activity into a build-in-public post and push it to your StratCMO Action Board as a drafted card. Use when the user wants to share progress, write a build-in-public/changelog/dev-diary post, or "post what I shipped". Reads git locally; only the post text leaves the machine.
---

# Build-in-public → StratCMO

Turn what the founder just shipped into a short, human build-in-public post, and push it to their
StratCMO Action Board as a **drafted** card. The founder reviews it on the board and presses send.

**Privacy guarantee — state this to the user the first time:** their code never leaves the machine.
This skill reads `git log`/`git diff` locally to understand what changed, then sends only the final
post text to StratCMO. It posts nothing publicly itself.

## Prerequisites (check, and help set up if missing)

- `STRATCMO_TOKEN` env var — a CLI token starting with `scmo_`. If unset, tell the user to mint one
  in StratCMO (Settings → CLI tokens) and `export STRATCMO_TOKEN=scmo_…`.
- `STRATCMO_SLUG` env var — their company slug (e.g. `acme-com`), so the card lands on the right board.
- `STRATCMO_URL` — only if self-hosted (defaults to https://stratcmo.app).

## Steps

1. **Read recent local activity** (on the user's machine — nothing is uploaded):
   - `git log --oneline -n 20`
   - `git diff --stat HEAD~5..HEAD` (adjust the range to what looks like recent work)
   - Optionally skim notable diffs to understand the *user-facing* change, not just file churn.

2. **Draft the post.** Write it in the founder's voice — a developer diary, not a press release:
   - Lead with the concrete thing that changed and why it matters to a user.
   - One idea. Specific. A real number or detail beats adjectives.
   - No hype, no em-dashes, no "I'm thrilled to announce". Sound like one person typing quickly.
   - For `--platform x`: keep it tight, one idea, under ~280 chars.
   - For `--platform linkedin`: a short hook + a couple of small paragraphs + a real takeaway.
   - Ask the user which platform if it's ambiguous; default to `x`.

3. **Show the draft to the user and get a yes** before pushing. Offer to tweak it.

4. **Push it** to their board (this is the only network call; it creates a *drafted* card, it does
   not post publicly):

   ```bash
   python push_card.py --platform x --title "<short title>" --body-file <(cat <<'POST'
   <the drafted post text>
   POST
   )
   ```

   Or pipe the body via stdin:

   ```bash
   echo "<the drafted post text>" | python push_card.py --platform x --title "<short title>"
   ```

   (`push_card.py` lives next to this SKILL.md. It reads `STRATCMO_TOKEN`/`STRATCMO_URL`/`STRATCMO_SLUG`.)

5. **Confirm**: tell the user it's a drafted card on their Action Board, and that they review and press
   send there. Never imply it was published.

## Notes

- If the push fails with 401, the token is missing/invalid — point them back to minting one.
- If `git` shows nothing recent, say so and ask what they want to highlight instead of inventing work.
- Keep it honest: post what actually shipped.
