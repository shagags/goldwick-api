from fastapi import FastAPI
import os, requests, pandas as pd

TOKEN = os.getenv("OANDA_TOKEN")
BASE_URL = "https://api-fxpractice.oanda.com"
INSTRUMENT = "XAU_USD"

app = FastAPI()

@app.get("/")
def root():
    return {"status": "online"}

@app.get("/signal")
def signal():
    # minimal placeholder: just prove the API works
    return {"status": "online"}

import requests, pandas as pd, datetime as dt, os

TOKEN = os.getenv("OANDA_TOKEN")
BASE_URL = "https://api-fxpractice.oanda.com"
INSTRUMENT = "XAU_USD"
EMA_SPAN  = 50
SL_PIPS   = 5
TP_PIPS   = 7.5

def fetch_candles(count=60):
    url = f"{BASE_URL}/v3/instruments/{INSTRUMENT}/candles"
    r = requests.get(url,
                     params={"count": count, "granularity": "M1", "price":"M"},
                     headers={"Authorization": f"Bearer {TOKEN}"},
                     timeout=10)
    r.raise_for_status()
    data = []
    for c in r.json()["candles"]:
        m = c["mid"]
        data.append(dict(time=c["time"],
                         open=float(m["o"]),
                         high=float(m["h"]),
                         low=float(m["l"]),
                         close=float(m["c"])))
    return pd.DataFrame(data)

@app.post("/signal")
@app.get("/signal")
async def signal():
    df = fetch_candles()
    df["ema"] = df["close"].ewm(span=EMA_SPAN, adjust=False).mean()

    prev, cur = df.iloc[-2], df.iloc[-1]
    body  = abs(prev.close - prev.open) + 1e-6
    up_w  = prev.high - max(prev.open, prev.close)
    low_w = min(prev.open, prev.close) - prev.low
    trend_up   = prev.close > prev.ema
    trend_down = prev.close < prev.ema

    if trend_up and low_w/body > .5 and prev.low < prev.ema <= prev.close:
        entry = cur.open
        return {
            "direction": "BUY",
            "entry": round(entry,2),
            "sl":   round(entry-SL_PIPS,2),
            "tp":   round(entry+TP_PIPS,2),
            "timestamp": dt.datetime.utcnow().isoformat()
        }
    if trend_down and up_w/body > .5 and prev.high > prev.ema >= prev.close:
        entry = cur.open
        return {
            "direction": "SELL",
            "entry": round(entry,2),
            "sl":   round(entry+SL_PIPS,2),
            "tp":   round(entry-TP_PIPS,2),
            "timestamp": dt.datetime.utcnow().isoformat()
        }
    return {"direction":"NONE","msg":"no valid wick right now"}

