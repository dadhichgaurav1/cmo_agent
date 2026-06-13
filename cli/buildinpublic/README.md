# StratCMO build-in-public skill

A Claude Code skill that turns your recent git activity into a build-in-public post and pushes it
to your [StratCMO](https://stratcmo.app) Action Board as a **drafted** card. You review it on the
board and press send — the skill never posts publicly itself.

**Your code never leaves your machine.** The skill reads `git log`/`git diff` locally; only the
final post text is sent to StratCMO (one HTTP request).

## Install

Copy this folder into your project's (or personal) Claude Code skills directory, e.g.:

```bash
cp -r cli/buildinpublic ~/.claude/skills/buildinpublic
```

## Configure

Mint a CLI token in StratCMO (Settings → CLI tokens), then:

```bash
export STRATCMO_TOKEN=scmo_xxxxxxxx        # the token you minted
export STRATCMO_SLUG=your-company-com      # which board the card lands on
# export STRATCMO_URL=https://your-host    # only if self-hosting
```

## Use

In Claude Code, just say things like:

> post what I shipped today
> write a build-in-public post about the last few commits

Claude reads your recent commits, drafts a post in your voice, shows it to you, and on your OK pushes
it as a drafted card to your Action Board.

### Manual push (without the agent)

```bash
echo "Shipped the new diff view. It's 3x faster on big repos." \
  | python push_card.py --platform x --title "Faster diff view"
```

Requires Python 3 (standard library only — no dependencies).
