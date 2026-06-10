#!/usr/bin/env python3
"""
backtest_v2.py — Revised backtest with differentiating risk metrics.

Metrics:
  1. Realized-APY volatility (std dev of weekly yield stream)
  2. Exposure-weighted sigma + % capital-weeks in prediction_class="Down"
  3. Depeg stress: −3% haircut to highest-sigma pool applied to BOTH strategies
     at the first date each strategy holds that pool on/after Feb 2026.
  4. Net-of-friction APY: 5 bps per one-way rebalance leg at 7d / 14d / 30d
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json, os

os.makedirs("docs/img", exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────────────
hist_df = pd.read_csv("data/arbitrum_pool_histories.csv")
hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
hist_df = hist_df.sort_values('timestamp')

chain_tvl_df = pd.read_csv("data/arbitrum_chain_tvl_daily.csv")
chain_tvl_df['date'] = pd.to_datetime(chain_tvl_df['date'])
chain_tvl_df = chain_tvl_df.sort_values('date')

snapshot_df = pd.read_csv("data/arbitrum_pools_snapshot.csv")

# ── Universe ───────────────────────────────────────────────────────────────────
universe_pools = snapshot_df[
    (snapshot_df['stablecoin'] == True) &
    (snapshot_df['tvlUsd'] >= 5_000_000) &
    (snapshot_df['ilRisk'] == 'no') &
    (snapshot_df['outlier'] == False)
]['pool'].tolist()
print(f"Universe: {len(universe_pools)} pools")

hist_universe = hist_df[hist_df['pool'].isin(universe_pools)].copy()

sigma_map  = snapshot_df.set_index('pool')['sigma'].to_dict()
pred_map   = snapshot_df.set_index('pool')['prediction_class'].to_dict()
symbol_map = snapshot_df.set_index('pool')['symbol'].to_dict()
proj_map   = snapshot_df.set_index('pool')['project'].to_dict()

# Highest-sigma pool WITH historical data (depeg proxy)
covered_pools = set(hist_universe['pool'].unique())
uni_sigma_covered = {p: sigma_map.get(p, 0) for p in universe_pools if p in covered_pools}
highest_sigma_pool = max(uni_sigma_covered, key=uni_sigma_covered.get)
uni_sigma = uni_sigma_covered
HS_SIGMA = uni_sigma[highest_sigma_pool]
HS_SYMBOL = symbol_map.get(highest_sigma_pool, highest_sigma_pool)
HS_PROJECT = proj_map.get(highest_sigma_pool, '')
print(f"Depeg proxy: {HS_SYMBOL} ({HS_PROJECT})  sigma={HS_SIGMA:.4f}  "
      f"pred={pred_map.get(highest_sigma_pool,'?')}")

DEPEG_WINDOW_START = pd.Timestamp('2026-02-01')
DEPEG_HAIRCUT      = -0.03   # −3% one-time hit when holding the pool

# ── Chain TVL 30d momentum ─────────────────────────────────────────────────────
chain_tvl_df['tvl_30d_ago'] = chain_tvl_df['tvl_usd'].shift(30)
chain_tvl_df['momentum_30d'] = (
    (chain_tvl_df['tvl_usd'] - chain_tvl_df['tvl_30d_ago']) / chain_tvl_df['tvl_30d_ago']
)
mom_dict = dict(zip(chain_tvl_df['date'].dt.normalize(), chain_tvl_df['momentum_30d']))

# ── Core simulation ────────────────────────────────────────────────────────────
def run_backtest(rebalance_days: int, apply_depeg: bool = False):
    start_date = hist_universe['timestamp'].min()
    end_date   = hist_universe['timestamp'].max()
    dates = pd.date_range(start_date, end_date, freq='D')

    pv_router = 10_000.0
    pv_naive  = 10_000.0
    alloc_r   = {}
    alloc_n   = {}
    last_reb  = None
    turnover  = 0.0
    n_reb     = 0

    depeg_router_done = False
    depeg_naive_done  = False

    port_rows  = []
    naive_rows = []
    alloc_log  = []   # for sigma / prediction tracking

    for current_date in dates:
        day_data = hist_universe[hist_universe['timestamp'] == current_date]
        if day_data.empty:
            continue

        momentum = mom_dict.get(current_date.normalize(), 0)

        # ── Depeg haircut: applied the first time each strategy holds the pool
        #    on or after DEPEG_WINDOW_START ────────────────────────────────────
        if apply_depeg and current_date >= DEPEG_WINDOW_START:
            if not depeg_router_done and highest_sigma_pool in alloc_r:
                w = alloc_r[highest_sigma_pool]
                pv_router *= (1 + w * DEPEG_HAIRCUT)
                depeg_router_done = True
                print(f"  Router depeg hit on {current_date.date()}: "
                      f"weight={w:.2%}  impact={w*DEPEG_HAIRCUT*100:.2f}%")
            if not depeg_naive_done and highest_sigma_pool in alloc_n:
                w = alloc_n[highest_sigma_pool]
                pv_naive *= (1 + w * DEPEG_HAIRCUT)
                depeg_naive_done = True
                print(f"  Naive  depeg hit on {current_date.date()}: "
                      f"weight={w:.2%}  impact={w*DEPEG_HAIRCUT*100:.2f}%")

        # ── Daily returns ──────────────────────────────────────────────────────
        dr_r = 0.0
        for pool, w in alloc_r.items():
            row = day_data[day_data['pool'] == pool]
            if not row.empty:
                apy = row['apy_pct'].values[0] / 100
                dr_r += w * ((1 + apy) ** (1/365) - 1)

        dr_n = 0.0
        for pool, w in alloc_n.items():
            row = day_data[day_data['pool'] == pool]
            if not row.empty:
                apy = row['apy_pct'].values[0] / 100
                dr_n += w * ((1 + apy) ** (1/365) - 1)

        pv_router *= (1 + dr_r)
        pv_naive  *= (1 + dr_n)

        port_rows.append({'date': current_date, 'value': pv_router,
                          'daily_ret': dr_r, 'momentum': momentum})
        naive_rows.append({'date': current_date, 'value': pv_naive,
                           'daily_ret': dr_n})

        # ── Rebalance ──────────────────────────────────────────────────────────
        if last_reb is None or (current_date - last_reb).days >= rebalance_days:
            day_meta = pd.merge(
                day_data,
                snapshot_df[['pool', 'sigma', 'mu', 'prediction_class']],
                on='pool', how='left'
            ).dropna(subset=['apy_pct', 'sigma'])

            if day_meta.empty:
                continue

            # Naive: 100% to highest-APY pool
            best_naive = day_meta.loc[day_meta['apy_pct'].idxmax(), 'pool']
            new_naive  = {best_naive: 1.0}

            # Router
            if momentum < -0.15:
                safest   = day_meta.loc[day_meta['sigma'].idxmin(), 'pool']
                new_alloc = {safest: 1.0}
            else:
                t30 = current_date - pd.Timedelta(days=30)
                mean30 = (hist_universe[
                    (hist_universe['timestamp'] > t30) &
                    (hist_universe['timestamp'] <= current_date)]
                    .groupby('pool')['apy_pct'].mean()
                    .reset_index().rename(columns={'apy_pct': 'mean30'}))
                day_meta = pd.merge(day_meta, mean30, on='pool', how='left')
                day_meta['mean30'] = day_meta['mean30'].fillna(day_meta['apy_pct'])
                day_meta['penalty'] = np.where(day_meta['prediction_class'] == 'Down', 0.5, 1.0)
                day_meta['score'] = (day_meta['mean30'] / (1 + 100 * day_meta['sigma'])) * day_meta['penalty']
                day_meta = day_meta.sort_values('score', ascending=False)

                new_alloc = {}
                rem = 1.0
                for _, r in day_meta.iterrows():
                    if rem <= 1e-9:
                        break
                    w = min(0.4, rem)
                    new_alloc[r['pool']] = w
                    rem -= w

            # One-way turnover
            all_p = set(alloc_r) | set(new_alloc)
            to = sum(abs(new_alloc.get(p, 0) - alloc_r.get(p, 0)) for p in all_p) / 2
            turnover += to
            n_reb += 1

            # Friction: 5 bps per one-way leg
            pv_router *= (1 - to * 0.0005)

            # Log router allocation
            for pool, w in new_alloc.items():
                alloc_log.append({
                    'date': current_date, 'pool': pool, 'weight': w,
                    'sigma': sigma_map.get(pool, 0),
                    'pred': pred_map.get(pool, 'Unknown')
                })

            alloc_r  = new_alloc
            alloc_n  = new_naive
            last_reb = current_date

    port_df  = pd.DataFrame(port_rows)
    naive_df = pd.DataFrame(naive_rows)
    alloc_df = pd.DataFrame(alloc_log)

    # Weekly yield streams (annualised %)
    port_df['week']  = port_df['date'].dt.to_period('W')
    naive_df['week'] = naive_df['date'].dt.to_period('W')
    weekly_r = port_df.groupby('week')['daily_ret'].sum() * 52 * 100
    weekly_n = naive_df.groupby('week')['daily_ret'].sum() * 52 * 100

    # Exposure-weighted sigma + Down-pool fraction
    if not alloc_df.empty:
        alloc_df['week'] = alloc_df['date'].dt.to_period('W')
        ew_sigma  = alloc_df.groupby('week').apply(
            lambda g: (g['weight'] * g['sigma']).sum() / g['weight'].sum()
        )
        down_frac = alloc_df.groupby('week').apply(
            lambda g: g.loc[g['pred'] == 'Down', 'weight'].sum()
        )
    else:
        ew_sigma  = pd.Series(dtype=float)
        down_frac = pd.Series(dtype=float)

    return dict(port_df=port_df, naive_df=naive_df,
                weekly_r=weekly_r, weekly_n=weekly_n,
                ew_sigma=ew_sigma, down_frac=down_frac,
                turnover=turnover, n_reb=n_reb)


# ── Run scenarios ──────────────────────────────────────────────────────────────
print("\nRunning 7d (no depeg)...")
r7  = run_backtest(7,  apply_depeg=False)
print("Running 14d (no depeg)...")
r14 = run_backtest(14, apply_depeg=False)
print("Running 30d (no depeg)...")
r30 = run_backtest(30, apply_depeg=False)
print("Running 7d (with depeg stress)...")
r7s = run_backtest(7,  apply_depeg=True)


# ── Stats helpers ──────────────────────────────────────────────────────────────
def ann_return(df):
    days  = (df['date'].max() - df['date'].min()).days
    years = days / 365.25
    tot   = df['value'].iloc[-1] / df['value'].iloc[0] - 1
    return (1 + tot) ** (1 / years) - 1, years

def max_dd(df):
    df = df.copy()
    df['cm'] = df['value'].cummax()
    return ((df['value'] - df['cm']) / df['cm']).min()

def stress_window(df):
    s = df[(df['date'] >= DEPEG_WINDOW_START) &
           (df['date'] <= pd.Timestamp('2026-05-31'))].copy()
    if s.empty:
        return 0, 0
    ret = s['value'].iloc[-1] / s['value'].iloc[0] - 1
    s['cm'] = s['value'].cummax()
    dd = ((s['value'] - s['cm']) / s['cm']).min()
    return ret * 100, dd * 100


# ── Build summary table ────────────────────────────────────────────────────────
rows = {}
for tag, res in [('7d', r7), ('14d', r14), ('30d', r30)]:
    ar_r, yrs = ann_return(res['port_df'])
    ar_n, _   = ann_return(res['naive_df'])
    dd_r = max_dd(res['port_df'])
    dd_n = max_dd(res['naive_df'])
    vol_r = res['weekly_r'].std()
    vol_n = res['weekly_n'].std()
    ew_s  = res['ew_sigma'].mean() if not res['ew_sigma'].empty else 0
    dp    = res['down_frac'].mean() * 100 if not res['down_frac'].empty else 0
    ann_to = res['turnover'] / yrs * 100
    rows[tag] = dict(
        router_apy=ar_r*100, naive_apy=ar_n*100,
        router_apy_vol=vol_r, naive_apy_vol=vol_n,
        router_dd=dd_r*100, naive_dd=dd_n*100,
        ew_sigma=ew_s, down_pct=dp,
        ann_turnover=ann_to, years=yrs
    )

# Stress window (7d with depeg)
sr_r, sdd_r = stress_window(r7s['port_df'])
sr_n, sdd_n = stress_window(r7s['naive_df'])

print("\n=== SUMMARY ===")
for tag, s in rows.items():
    print(f"\n{tag} rebalance:")
    print(f"  Router APY (net friction): {s['router_apy']:.2f}%  |  Naive APY: {s['naive_apy']:.2f}%")
    print(f"  Router APY vol (σ): {s['router_apy_vol']:.2f}%  |  Naive APY vol: {s['naive_apy_vol']:.2f}%")
    print(f"  Router max DD: {s['router_dd']:.4f}%  |  Naive max DD: {s['naive_dd']:.4f}%")
    print(f"  EW sigma: {s['ew_sigma']:.4f}  |  Down exposure: {s['down_pct']:.1f}%")
    print(f"  Annual turnover: {s['ann_turnover']:.0f}%")

print(f"\nDepeg stress (7d, −3% {HS_SYMBOL} at Feb 2026):")
print(f"  Router period return: {sr_r:.2f}%  |  Naive: {sr_n:.2f}%")
print(f"  Router max DD: {sdd_r:.4f}%  |  Naive max DD: {sdd_n:.4f}%")


# ── PLOTS ──────────────────────────────────────────────────────────────────────
plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {'router': '#2563EB', 'naive': '#DC2626'}

# 1. Equity curves — 7d / 14d / 30d
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for ax, (tag, res) in zip(axes, [('7d', r7), ('14d', r14), ('30d', r30)]):
    ax.plot(res['port_df']['date'], res['port_df']['value'],
            label=f"Router ({rows[tag]['router_apy']:.1f}% net)", color=COLORS['router'], lw=1.5)
    ax.plot(res['naive_df']['date'], res['naive_df']['value'],
            label=f"Naive ({rows[tag]['naive_apy']:.1f}%)", color=COLORS['naive'], lw=1.5, alpha=0.8)
    ax.axvline(DEPEG_WINDOW_START, color='orange', ls='--', lw=1, label='Feb 2026')
    ax.set_title(f'Equity Curve — {tag} rebalance')
    ax.set_ylabel('Portfolio Value ($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig('docs/img/equity_curves_rebalance_comparison.png', dpi=120)
plt.close()

# 2. Depeg stress scenario
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(r7s['port_df']['date'], r7s['port_df']['value'],
        label=f'Router + depeg (DD={sdd_r:.3f}%)', color=COLORS['router'], lw=2)
ax.plot(r7s['naive_df']['date'], r7s['naive_df']['value'],
        label=f'Naive + depeg (DD={sdd_n:.3f}%)', color=COLORS['naive'], lw=2, alpha=0.8)
ax.plot(r7['port_df']['date'], r7['port_df']['value'],
        label='Router (no stress)', color=COLORS['router'], lw=1, ls='--', alpha=0.4)
ax.plot(r7['naive_df']['date'], r7['naive_df']['value'],
        label='Naive (no stress)', color=COLORS['naive'], lw=1, ls='--', alpha=0.4)
ax.axvline(DEPEG_WINDOW_START, color='orange', lw=2, ls='--', label=f'Depeg event ({HS_SYMBOL}, −3%)')
ax.set_title(f'Depeg Stress: −3% Haircut to {HS_SYMBOL} ({HS_PROJECT}) at Feb 2026')
ax.set_ylabel('Portfolio Value ($)')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
ax.legend()
plt.tight_layout()
plt.savefig('docs/img/depeg_stress_scenario.png', dpi=120)
plt.close()

# 3. Weekly APY volatility
fig, axes = plt.subplots(1, 3, figsize=(18, 4))
for ax, (tag, res) in zip(axes, [('7d', r7), ('14d', r14), ('30d', r30)]):
    wr = res['weekly_r']
    wn = res['weekly_n']
    ax.plot(wr.index.to_timestamp(), wr.values,
            label=f'Router σ={wr.std():.2f}%', color=COLORS['router'], lw=1.2)
    ax.plot(wn.index.to_timestamp(), wn.values,
            label=f'Naive σ={wn.std():.2f}%', color=COLORS['naive'], lw=1.2, alpha=0.8)
    ax.axhline(0, color='black', lw=0.5)
    ax.set_title(f'Weekly Yield Stream — {tag}')
    ax.set_ylabel('Annualised Weekly Yield (%)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig('docs/img/weekly_apy_volatility.png', dpi=120)
plt.close()

# 4. Risk profile over time (7d router)
if not r7['ew_sigma'].empty:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax1.plot(r7['ew_sigma'].index.to_timestamp(), r7['ew_sigma'].values,
             color=COLORS['router'], lw=1.5, label='Router EW-sigma')
    ax1.set_ylabel('Exposure-Weighted Sigma')
    ax1.set_title('Router Risk Profile Over Time (7d rebalance)')
    ax1.legend()
    ax2.fill_between(r7['down_frac'].index.to_timestamp(),
                     r7['down_frac'].values * 100,
                     alpha=0.5, color=COLORS['naive'],
                     label='% capital in "Down" pools')
    ax2.set_ylabel('% Capital in "Down" Pools')
    ax2.set_xlabel('Date')
    ax2.legend()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig('docs/img/risk_profile_over_time.png', dpi=120)
    plt.close()

print("All charts saved to docs/img/")

# ── Persist stats for report ───────────────────────────────────────────────────
report_data = {
    'stats': {k: {kk: float(vv) for kk, vv in v.items()} for k, v in rows.items()},
    'stress': {
        'router_period_return': float(sr_r),
        'naive_period_return':  float(sr_n),
        'router_max_dd':        float(sdd_r),
        'naive_max_dd':         float(sdd_n),
    },
    'depeg_proxy': {
        'symbol': HS_SYMBOL,
        'project': HS_PROJECT,
        'sigma': float(HS_SIGMA),
        'prediction': pred_map.get(highest_sigma_pool, '?'),
        'haircut_pct': DEPEG_HAIRCUT * 100,
    }
}
with open('docs/backtest_stats.json', 'w') as f:
    json.dump(report_data, f, indent=2)
print("Stats saved to docs/backtest_stats.json")
