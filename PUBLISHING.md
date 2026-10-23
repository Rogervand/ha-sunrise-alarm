# Publishing checklist

1. Replace every `Rogervand` (manifest.json, README.md, the card's `documentationURL`).
   `grep -rn Rogervand .`
2. Create a **public** GitHub repo named `ha-sunrise-alarm` and push.
3. Repo settings: add a description, enable Issues, add topics
   (`home-assistant`, `hacs`, `hacs-integration`, `alarm-clock`, `sonos`).
4. Confirm the **Validate** workflow passes (HACS, Hassfest, Tests).
5. Create a GitHub **release** (not just a tag) named `v0.1.0`. The Release workflow
   checks the tag matches the version in `manifest.json`, `const.py` and the card.
6. Fork `hacs/default`, branch from `master`, add `Rogervand/ha-sunrise-alarm`
   to the `integration` file in alphabetical order, open a PR. Its bots re-run the checks.

## Bumping a version
Update the version in all three places: `manifest.json`, `const.py` (`VERSION`) and
`frontend/sunrise-alarm-card.js` (`CARD_VERSION`). The card URL includes the version,
so browsers fetch the new card after an update.
