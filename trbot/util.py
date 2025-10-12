from zoneinfo import ZoneInfo
import json

from .tbsecrets import ALPACA_SECRETS


ALL_SYMBOLS: list[str] = [
    "AAPL", "ABNB", "BBY", "DASH", "DELL", "EBAY", "F", "GE", "GOOG", "HIMS",
    "HPQ", "INTC", "LOGI", "NIO", "NVDA", "PANW", "PEP", "PLTR", "QCOM",
    "ROST", "SHOP", "SMCI", "SPY", "TGT", "WMT", "XLF"
]

MY_TIMEZONE = ZoneInfo("America/New_York")

def alpaca_keys(acct_name: str) -> tuple[str, str]:
    """ Access my keys from alpaca """
    return (ALPACA_SECRETS[acct_name]["api_key"], ALPACA_SECRETS[acct_name]["secret_key"])

