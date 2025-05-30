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
