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

# allow GPT (which uses POST) to hit the same route
@app.post("/signal")
async def signal_post():
    return signal()
