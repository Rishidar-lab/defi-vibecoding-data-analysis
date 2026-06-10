# Manus Playbook — GitHub Operations & Submission Prep

Execute in order. Stop and ask the user at any step marked **[USER ACTION]**.

## 0. Pre-flight secret hygiene
- Never commit `.env`, API keys, RPC URLs with embedded keys, wallet seeds, or keystores.
- `grep -rE "(api[_-]?key|secret|seed|mnemonic|private[_-]?key)" --include='*' .` before every push; investigate any hit.
- Variables go in `.env.example` with placeholder values only.

## 1. Repository setup
```bash
gh --version || sudo apt install gh          # or: brew install gh
gh auth status || gh auth login              # [USER ACTION] browser/device-code login
cd defi-vibecoding-data-analysis
git init -b main
git add .
git commit -m "feat: add initial dataset and research analysis"
gh repo create defi-vibecoding-data-analysis --public \
  --source=. --remote=origin --push \
  --description "Arbitrum DeFi dataset + research for a Vibekit/Trailblazer 2.0 strategy contribution"
gh repo edit --default-branch main
```

## 2. Regenerate the full dataset (open-egress machine, e.g. CYPHERDOME)
```bash
python -m venv .venv && source .venv/bin/activate
pip install requests pandas
python scripts/fetch_dataset.py
git add data/ && git commit -m "data: full daily TVL, all-Arbitrum pool snapshot, pool histories" && git push
```

## 3. Documentation checklist
- Root `README.md`: project purpose (Trailblazer 2.0 / Vibekit participation), dataset sources with links, pointer to `docs/research_analysis.md`, setup + reproduction instructions. (Already drafted — review and adjust.)
- Keep `LICENSE` (MIT) and `data/README.md` in sync with any schema changes.

## 4. Vibekit contribution flow (required order per CONTRIBUTIONS.md)
1. Search open issues at https://github.com/EmberAGI/arbitrum-vibekit/issues for duplicates.
2. Open a new issue using the appropriate template (agent_template.yml or mcp_server.yml) describing the planned contribution; reference this repo.
3. **Wait for Ember team approval comment before building.**
4. Fork `EmberAGI/arbitrum-vibekit`, build under `typescript/community/`, follow `TESTING.md`, run `pnpm test`.
5. Open PR referencing the issue number.

## 5. Trailblazer submission
- Submit the deployed agent/template through the form linked from
  https://blog.arbitrum.foundation/trailblazer-2-0-1m-in-grants-to-power-agentic-defi-on-arbitrum/
  including the GitHub repo link and a short utility/performance write-up.
- **[USER ACTION]** Any wallet signature, KYC, or identity verification the Foundation requires for payout.
- **[USER ACTION]** Confirm on the official blog/Discord that the program is still accepting submissions before filing.

## 6. Continuous improvement
- Cron/scheduled re-run of `scripts/fetch_dataset.py` (weekly) + commit, e.g. a GitHub Action with `schedule:`.
- Track relevant Vibekit issues/discussions; keep the research doc's findings section updated as regimes change.

## Safety constraints (binding)
- Read-only data access; **no mainnet transactions** from this repo or its automation.
- Testnets only for any execution experiments unless the user explicitly authorizes otherwise.
- No exploitative/manipulative strategy work; document limitations; no financial guarantees in any published material.
