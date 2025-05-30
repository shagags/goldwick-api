from fastapi import FastAPI, HTTPException
import os, requests, pandas as pd, datetime as dt

# ---- CONFIG ------------------------------------------------------------
TOKEN      = os.getenv("OANDA_TOKEN")                      #  <-- env-var name
BASE_URL   = "https://api-fxpractice.oanda.com"            # change to fxtrade for live
INSTRUMENT = "XAU_USD"
EMA_SPAN   = 50
SL_PIPS    = 5
TP_PIPS    = 7.5
# ------------------------------------------------------------------------

app = FastAPI()

@app.get("/")
def root():
    return {"status": "goldwick-api live"}

def fetch_candles(count=60):
    url = f"{BASE_URL}/v3/instruments/{INSTRUMENT}/candles"
    params  = {"count": count, "granularity": "M1", "price": "M"}
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    if r.status_code == 401:
        raise HTTPException(502, "OANDA 401 – bad or missing token")
    r.raise_for_status()
    rows = []
    for c in r.json()["candles"]:
        m = c["mid"]
        rows.append(
            dict(time=c["time"],
                 open=float(m["o"]),
                 high=float(m["h"]),
                 low=float(m["l"]),
                 close=float(m["c"])))
    return pd.DataFrame(rows)

# ----------------- core signal logic ------------------------------------
@app.get("/signal")
def signal():
    df = fetch_candles()
    df["ema"] = df["close"].ewm(span=EMA_SPAN, adjust=False).mean()
    prev, cur = df.iloc[-2], df.iloc[-1]

    body  = abs(prev.close - prev.open) + 1e-6
    up_w  = prev.high - max(prev.open, prev.close)
    lo_w  = min(prev.open, prev.close) - prev.low
    trend_up   = prev.close > prev.ema
    trend_down = prev.close < prev.ema

    if trend_up and lo_w/body > .5 and prev.low < prev.ema <= prev.close:
        entry = cur.open
        return {
            "direction": "BUY",
            "entry": round(entry,2),
            "sl":   round(entry - SL_PIPS,2),
            "tp":   round(entry + TP_PIPS,2),
            "timestamp": dt.datetime.utcnow().isoformat()
        }
    if trend_down and up_w/body > .5 and prev.high > prev.ema >= prev.close:
        entry = cur.open
        return {
            "direction": "SELL",
            "entry": round(entry,2),
            "sl":   round(entry + SL_PIPS,2),
            "tp":   round(entry - TP_PIPS,2),
            "timestamp": dt.datetime.utcnow().isoformat()
        }
    return {"direction": "NONE", "msg": "no valid setup right now"}

# allow GPT (which uses POST) to hit the same route
@app.post("/signal")
async def signal_post():
    return signal()
