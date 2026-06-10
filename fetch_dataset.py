#!/usr/bin/env python3
"""
fetch_dataset.py — Build the full Arbitrum DeFi vibecoding dataset from free,
no-auth DefiLlama endpoints.

Run on any machine with open internet egress (no API key required):

    pip install requests pandas
    python scripts/fetch_dataset.py

Outputs (written to data/):
  - arbitrum_chain_tvl_daily.csv      Full daily chain TVL history
  - arbitrum_pools_snapshot.csv       All Arbitrum pools (APY, TVL, sigma, mu,
                                      predictions, IL risk, stablecoin flag)
  - arbitrum_pool_histories.csv       Daily APY+TVL history for top pools of
                                      the Vibekit launch protocols
  - arb_vibecoding_dataset.csv        Merged long-format dataset
                                      (timestamp, asset, protocol, chain, apy,
                                      tvl_usd, apy_vol_30d, risk fields)

Sources (cite DefiLlama when publishing):
  https://api.llama.fi/v2/historicalChainTvl/Arbitrum
  https://yields.llama.fi/pools
  https://yields.llama.fi/chart/{pool_id}
API docs: https://api-docs.defillama.com/
"""

import time
import requests
import pandas as pd

VIBEKIT_PROTOCOLS = {
    # Vibekit launch integrations (Trailblazer 2.0 blog, June 2025)
    "aave-v3", "gmx-v2-perps", "gmx-v1", "pendle",
    "camelot-v2", "camelot-v3",
    # high-TVL Arbitrum stablecoin venues worth benchmarking against
    "sky-lending", "spark-savings", "fluid-lending", "compound-v3",
}
TOP_N_HISTORIES = 25          # pool histories to download
MIN_TVL_USD = 100_000         # ignore dust pools
UA = {"User-Agent": "defi-vibecoding-data-analysis/0.1 (research)"}


def get_json(url: str, retries: int = 3):
    for i in range(retries):
        r = requests.get(url, headers=UA, timeout=60)
        if r.ok:
            return r.json()
        time.sleep(2 ** i)
    r.raise_for_status()


def fetch_chain_tvl() -> pd.DataFrame:
    raw = get_json("https://api.llama.fi/v2/historicalChainTvl/Arbitrum")
    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"], unit="s").dt.date
    df = df.rename(columns={"tvl": "tvl_usd"})
    df.to_csv("data/arbitrum_chain_tvl_daily.csv", index=False)
    return df


def fetch_pools() -> pd.DataFrame:
    raw = get_json("https://yields.llama.fi/pools")["data"]
    df = pd.DataFrame(raw)
    arb = df[(df["chain"] == "Arbitrum") & (df["tvlUsd"] >= MIN_TVL_USD)].copy()
    pred = arb["predictions"].apply(pd.Series)
    arb["prediction_class"] = pred.get("predictedClass")
    arb["prediction_prob_pct"] = pred.get("predictedProbability")
    cols = ["pool", "project", "symbol", "chain", "tvlUsd", "apy", "apyBase",
            "apyReward", "apyMean30d", "sigma", "mu", "stablecoin", "ilRisk",
            "exposure", "outlier", "prediction_class", "prediction_prob_pct",
            "poolMeta"]
    arb = arb[[c for c in cols if c in arb.columns]]
    arb.to_csv("data/arbitrum_pools_snapshot.csv", index=False)
    return arb


def fetch_pool_histories(arb: pd.DataFrame) -> pd.DataFrame:
    focus = arb[arb["project"].isin(VIBEKIT_PROTOCOLS)]
    focus = focus.sort_values("tvlUsd", ascending=False).head(TOP_N_HISTORIES)
    frames = []
    for _, row in focus.iterrows():
        try:
            hist = get_json(f"https://yields.llama.fi/chart/{row['pool']}")["data"]
        except Exception as exc:               # noqa: BLE001
            print(f"skip {row['project']}/{row['symbol']}: {exc}")
            continue
        h = pd.DataFrame(hist)
        h["pool"] = row["pool"]
        h["project"] = row["project"]
        h["symbol"] = row["symbol"]
        frames.append(h)
        time.sleep(0.5)                        # be a polite API citizen
    out = pd.concat(frames, ignore_index=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.date
    out = out.rename(columns={"tvlUsd": "tvl_usd", "apy": "apy_pct"})
    out.to_csv("data/arbitrum_pool_histories.csv", index=False)
    return out


def build_merged(hist: pd.DataFrame, arb: pd.DataFrame) -> None:
    df = hist.sort_values(["pool", "timestamp"]).copy()
    df["apy_vol_30d"] = (
        df.groupby("pool")["apy_pct"].transform(lambda s: s.rolling(30).std())
    )
    meta = arb.set_index("pool")[["stablecoin", "ilRisk", "exposure",
                                  "sigma", "mu", "prediction_class"]]
    df = df.join(meta, on="pool")
    df["chain"] = "Arbitrum"
    df = df.rename(columns={"symbol": "asset", "project": "protocol"})
    df[["timestamp", "asset", "protocol", "chain", "apy_pct", "tvl_usd",
        "apy_vol_30d", "sigma", "mu", "stablecoin", "ilRisk", "exposure",
        "prediction_class"]].to_csv("data/arb_vibecoding_dataset.csv",
                                    index=False)


if __name__ == "__main__":
    print("1/4 chain TVL ..."); chain = fetch_chain_tvl()
    print("2/4 pool snapshot ..."); pools = fetch_pools()
    print(f"   {len(pools)} Arbitrum pools >= ${MIN_TVL_USD:,}")
    print("3/4 pool histories ..."); hist = fetch_pool_histories(pools)
    print("4/4 merge ..."); build_merged(hist, pools)
    print("done — see data/")
