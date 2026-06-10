# defi-vibecoding-data-analysis

Dataset engineering and research groundwork for a **Vibekit** contribution targeting the
**Arbitrum Trailblazer 2.0** grant program ($1M pool, up to $10k/submission, retroactive).

- Selected competition, rankings, methodology, EDA, risks: [`docs/research_analysis.md`](docs/research_analysis.md)
- Dataset fields & provenance: [`data/README.md`](data/README.md)
- GitHub/submission operations playbook: [`docs/manus_github_workflow.md`](docs/manus_github_workflow.md)

## Reproduce
```bash
python -m venv .venv && source .venv/bin/activate
pip install requests pandas
python scripts/fetch_dataset.py   # regenerates full dataset into data/
```

## Sources
DefiLlama free API (api.llama.fi, yields.llama.fi — no auth; data © DefiLlama, cited per their FAQ);
Arbitrum Foundation blog; EmberAGI/arbitrum-vibekit repository.

## Disclaimers
Research only — not financial advice. Read-only data access; no mainnet transactions.
No secrets are committed; environment variables belong in `.env` (see `.env.example`).

MIT License.
