from fastapi import FastAPI
import os, requests, pandas as pd

TOKEN = os.getenv("41b3a96dcf48a9f9376c60f7804e3570-68be605e345f3a56e808e32a6b734e3a")
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

import pandas as pd, requests, datetime as dt, os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

TOKEN     = os.getenv("41b3a96dcf48a9f9376c60f7804e3570-68be605e345f3a56e808e32a6b734e3a")
ACCOUNT   = os.getenv("101-002-31761893-001")
BASE_URL  = "https://api-fxpractice.oanda.com"   # use api-fxtrade.oanda.com for live
INSTRUMENT= "XAU_USD"
EMA_SPAN  = 50
BUFF      = 0.05
TP_FACT   = 1.5

app = FastAPI(title="Gold Wick-Rejection API")

class Signal(BaseModel):
    direction: str
    entry: float
    sl: float
    tp: float
    timestamp: str

# ---------- fetch the last 60 one-minute candles ----------
def fetch_candles(count=60):
    endpoint = f"{BASE_URL}/v3/instruments/{INSTRUMENT}/candles"
    params   = {"count": count, "granularity": "M1", "price": "M"}
    headers  = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(endpoint, params=params, headers=headers, timeout=10)
    if r.status_code != 200:
        raise HTTPException(502, f"OANDA error {r.status_code}: {r.text}")

    rows = []
    for c in r.json()["candles"]:
        m = c["mid"]
        rows.append(dict(Open=float(m["o"]),
                         High=float(m["h"]),
                         Low=float(m["l"]),
                         Close=float(m["c"]),
                         Time=c["time"]))
    return pd.DataFrame(rows)

# ---------- trading logic ----------
def generate_signal():
    df = fetch_candles()
    df["EMA"] = df["Close"].ewm(span=EMA_SPAN, adjust=False).mean()
    prev = df.iloc[-2]

    trend_up   = prev.Close > prev.EMA
    trend_down = prev.Close < prev.EMA
    body  = abs(prev.Close - prev.Open) + 1e-6
    upper = prev.High - max(prev.Open, prev.Close)
    lower = min(prev.Open, prev.Close) - prev.Low

    if trend_up and lower/body > 0.5 and prev.Low < prev.EMA <= prev.Close:
        entry = df.iloc[-1].Open
        sl    = prev.Low - BUFF
        tp    = entry + (entry - sl) * TP_FACT
        return Signal(direction="long", entry=entry, sl=sl, tp=tp,
                      timestamp=dt.datetime.utcnow().isoformat())

    if trend_down and upper/body > 0.5 and prev.High > prev.EMA >= prev.Close:
        entry = df.iloc[-1].Open
        sl    = prev.High + BUFF
        tp    = entry - (sl - entry) * TP_FACT
        return Signal(direction="short", entry=entry, sl=sl, tp=tp,
                      timestamp=dt.datetime.utcnow().isoformat())

    return Signal(direction="none", entry=0, sl=0, tp=0,
                  timestamp=dt.datetime.utcnow().isoformat())

@app.post("/signal", response_model=Signal)
async def signal():
    return generate_signal()
