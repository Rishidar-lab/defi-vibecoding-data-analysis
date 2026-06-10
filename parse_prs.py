import subprocess, json

result = subprocess.run(
    ['gh', 'pr', 'list', '--repo', 'EmberAGI/arbitrum-vibekit', '--state', 'merged', '--limit', '300', '--json', 'number,title,author,mergedAt'],
    capture_output=True, text=True
)
prs = json.loads(result.stdout)
core = {'0xTomDaniel', 'varelaseb'}
community = [p for p in prs if p['author']['login'] not in core and not p['author'].get('is_bot', False)]
print(f"Total merged PRs: {len(prs)}")
print(f"Community PRs (non-core): {len(community)}")
for p in community[:10]:
    print(f"  #{p['number']}: {p['title']} by {p['author']['login']} ({p['mergedAt'][:10]})")
