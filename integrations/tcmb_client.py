"""
TCMB (Türkiye Cumhuriyet Merkez Bankası) Kur ve EVDS İstemcisi

Sağlanan veriler:
  - Döviz kurları  : today.xml — Ücretsiz, auth gerekmez (USD/TRY, EUR/TRY, GBP/TRY …)
  - Faiz oranları  : EVDS3 — TCMB_USERNAME + TCMB_PASSWORD gerekir (mock fallback)
  - Enflasyon      : EVDS3 — TCMB_USERNAME + TCMB_PASSWORD gerekir (mock fallback)
  - Para arzı      : EVDS3 — TCMB_USERNAME + TCMB_PASSWORD gerekir (mock fallback)

Döviz kurları için kayıt gerekmez:
  https://www.tcmb.gov.tr/kurlar/today.xml

EVDS3 için kayıt (ücretsiz) → kullanıcı adı + şifre gerekir:
  https://evds3.tcmb.gov.tr
.env'e ekle:
  TCMB_USERNAME=<eposta>
  TCMB_PASSWORD=<sifre>

EVDS3 API:
  POST https://evds3.tcmb.gov.tr/igmevdsms-dis/public/login
  POST https://evds3.tcmb.gov.tr/igmevdsms-dis/fe   (seri verisi)
"""
import logging
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from integrations.config import get_config

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Sabitler
# -----------------------------------------------------------------------

_XML_URL   = "https://www.tcmb.gov.tr/kurlar/today.xml"
_EVDS3_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"

# XML'de olmayan semboller için CrossOrder → CurrencyCode eşlemesi
_CODE_MAP: dict[str, str] = {
    "USD": "USD", "EUR": "EUR", "GBP": "GBP",
    "CHF": "CHF", "JPY": "JPY", "SAR": "SAR",
    "AED": "AED", "AUD": "AUD", "CAD": "CAD",
    "CNY": "CNY", "DKK": "DKK", "NOK": "NOK",
    "SEK": "SEK", "KWD": "KWD",
}

# Referans fallback kurları (TCMB'ye bağlanmadan)
_SPOT_RATES: dict[tuple[str, str], float] = {
    ("USD", "TRY"): 44.17,
    ("EUR", "TRY"): 50.96,
    ("GBP", "TRY"): 59.00,
    ("CHF", "TRY"): 56.20,
    ("JPY", "TRY"): 0.2780,
    ("SAR", "TRY"): 11.77,
    ("AED", "TRY"): 12.02,
    ("USD", "EUR"): 0.865,
    ("XAU", "USD"): 3040.0,
}

# EVDS3 seri kodları (POST /fe body'deki series alanı)
SERIES_INTEREST = {
    # TP.PY.P06.1HI = 1 haftalık mevduat ihalesi ağırlıklı ortalama faizi (~politika faizi)
    "policy_rate":          "TP.PY.P06.1HI",
    # TP.AOFOBAP = BIST gecelik repo ağırlıklı ortalama faizi
    "overnight_repo":       "TP.AOFOBAP",
    # TP.BISTTLREF.ORAN = Türk Lirası Gecelik Referans Faizi
    "tlref":                "TP.BISTTLREF.ORAN",
}
SERIES_INFLATION = {
    # (seri_kodu, formula) — formula: 0=level, 1=monthly%, 2=annual%
    "cpi_monthly": ("TP.TUKFIY2025.GENEL", "1"),
    "cpi_annual":  ("TP.TUKFIY2025.GENEL", "2"),
    "ppi_monthly": ("TP.TUFE1YI.T1",       "1"),
    "ppi_annual":  ("TP.TUFE1YI.T1",       "2"),
}
SERIES_MONEY_SUPPLY = {
    "m1": "TP.PA1.A",
    "m2": "TP.PA2.A",
    "m3": "TP.PA3.A",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------
# today.xml — gerçek zamanlı döviz kurları (auth gerekmez)
# -----------------------------------------------------------------------

def _fetch_xml_rates(timeout: float = 10.0) -> dict[str, dict]:
    """
    TCMB today.xml'den tüm kurları çeker.
    Döndürür: {"USD": {"buy": 44.13, "sell": 44.21, "unit": 1}, ...}
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(_XML_URL)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        rates: dict[str, dict] = {}
        for curr in root.findall("Currency"):
            code  = curr.get("CurrencyCode", "")
            unit  = int(curr.findtext("Unit", "1") or "1")
            buy   = curr.findtext("ForexBuying", "")
            sell  = curr.findtext("ForexSelling", "")
            if code and buy and sell:
                rates[code] = {
                    "buy":  float(buy),
                    "sell": float(sell),
                    "unit": unit,
                    "date": root.get("Date", ""),
                }
        return rates
    except Exception as exc:
        logger.warning("TCMB XML fetch failed: %s", exc)
        return {}


# -----------------------------------------------------------------------
# EVDS3 — oturum açarak seri verisi (TCMB_USERNAME + TCMB_PASSWORD ile)
# -----------------------------------------------------------------------

_session_cookies: dict = {}
_session_expires: float = 0.0


def _evds3_login(username: str, password: str, timeout: float = 10.0) -> bool:
    """EVDS3'e login olur, session cookie'yi depolar."""
    global _session_cookies, _session_expires
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{_EVDS3_BASE}/public/login?lang=TR",
                json={"username": username, "password": password},
            )
            if resp.status_code == 200:
                _session_cookies = dict(resp.cookies)
                _session_expires = datetime.now(timezone.utc).timestamp() + 3600
                logger.info("EVDS3 login başarılı")
                return True
            logger.warning("EVDS3 login başarısız: %d", resp.status_code)
    except Exception as exc:
        logger.warning("EVDS3 login hatası: %s", exc)
    return False


def _evds3_fetch(series_code: str, start_date: str, end_date: str,
                 username: str, password: str,
                 timeout: float = 10.0,
                 formula: str = "0",
                 frequency: str = "1") -> list[dict]:
    """
    EVDS3'ten seri verisi çeker.
    start_date/end_date: DD-MM-YYYY formatında
    """
    global _session_cookies, _session_expires

    # Gerekirse yeniden giriş yap
    now_ts = datetime.now(timezone.utc).timestamp()
    if now_ts >= _session_expires or not _session_cookies:
        if not _evds3_login(username, password, timeout):
            return []

    payload = {
        "type":             "json",
        "series":           series_code,
        "aggregationTypes": "avg",
        "formulas":         formula,
        "startDate":        start_date,
        "endDate":          end_date,
        "frequency":        frequency,  # 1=günlük, 3=haftalık, 5=aylık, 6=üç aylık
        "decimalSeperator": ".",
        "decimal":          "4",
        "dateFormat":       "1",
        "lang":             "EN",
        "yon":              None,
        "sira":             None,
        "ozelFormuller":    [],      # boş array olmalı — string değil
        "groupSeperator":   True,
        "isRaporSayfasi":   False,
    }
    cfg = get_config()
    api_key = cfg.tcmb_api_key or ""
    req_headers = {"key": api_key} if api_key else {}
    try:
        with httpx.Client(timeout=timeout, cookies=_session_cookies) as client:
            resp = client.post(f"{_EVDS3_BASE}/fe", json=payload, headers=req_headers)
            if resp.status_code in (401, 403):
                # Oturum süresi dolmuş, yeniden giriş yap
                _session_expires = 0
                if not _evds3_login(username, password, timeout):
                    return []
                resp = client.post(f"{_EVDS3_BASE}/fe", json=payload, headers=req_headers)
            resp.raise_for_status()
            data = resp.json()
        return data.get("items", [])
    except Exception as exc:
        logger.warning("EVDS3 fetch failed for %s: %s", series_code, exc)
        return []


def _latest_value(items: list[dict], series_code: str) -> float | None:
    """En son null-olmayan değeri döndürür. EVDS3 key'leri alt çizgili döndürür."""
    alt = series_code.replace(".", "_")
    for item in reversed(items):
        val = item.get(series_code) or item.get(alt)
        if val and val not in ("", None) and val != "ND":
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                continue
    return None


# -----------------------------------------------------------------------
# Döviz Kuru — today.xml primary, fallback mock
# -----------------------------------------------------------------------

def get_fx_rate(base_currency: str, quote_currency: str,
                amount: float | None = None, tenor: str = "spot") -> dict:
    """
    FX kuru — TCMB today.xml (gerçek zamanlı, auth gerekmez) veya referans fallback.
    TCMB yalnızca spot kur yayınlar; forward kurlar simüle edilir.
    """
    base  = base_currency.upper()
    quote = quote_currency.upper()
    rate: float | None = None
    source = "MOCK"

    # today.xml ile TRY cross kuru
    if quote == "TRY":
        xml_rates = _fetch_xml_rates(get_config().http_timeout)
        if xml_rates and base in xml_rates:
            info = xml_rates[base]
            mid  = (info["buy"] + info["sell"]) / 2
            # JPY gibi unit=100 olanları düzelt
            rate  = round(mid / info["unit"], 6)
            source = "LIVE_TCMB"

    if rate is None:
        key = (base, quote)
        if key in _SPOT_RATES:
            rate = round(_SPOT_RATES[key] * (1 + random.uniform(-0.005, 0.005)), 4)
        else:
            inv = (quote, base)
            if inv in _SPOT_RATES:
                rate = round(1 / _SPOT_RATES[inv] * (1 + random.uniform(-0.005, 0.005)), 4)
            else:
                rate = round(random.uniform(0.5, 50.0), 4)

    # Forward çarpanı
    tenor_mult = {"spot": 1.0, "1w": 1.001, "1m": 1.003,
                  "3m": 1.008, "6m": 1.015, "1y": 1.030}
    if tenor != "spot":
        rate = round(rate * tenor_mult.get(tenor, 1.0), 4)

    spread = round(rate * 0.003, 4)
    result: dict[str, Any] = {
        "base": base, "quote": quote, "tenor": tenor,
        "mid_rate": round(rate, 4),
        "bid": round(rate - spread, 4),
        "ask": round(rate + spread, 4),
        "source": source,
        "timestamp": _now(),
    }
    if amount is not None:
        result["base_amount"] = amount
        result["converted_amount"] = round(amount * rate, 2)
    return result


# -----------------------------------------------------------------------
# Faiz Oranları
# -----------------------------------------------------------------------

def get_interest_rates() -> dict:
    """TCMB politika faizi ve gecelik oranlar. EVDS3 veya mock fallback."""
    cfg = get_config()
    rates: dict[str, Any] = {}
    source = "MOCK"

    if cfg.is_tcmb_configured():
        today = datetime.now(timezone.utc)
        start = (today - timedelta(days=40)).strftime("%d-%m-%Y")
        end   = today.strftime("%d-%m-%Y")
        found = False
        for name, code in SERIES_INTEREST.items():
            items = _evds3_fetch(code, start, end,
                                 cfg.tcmb_username or "", cfg.tcmb_password or "",
                                 cfg.http_timeout)
            val = _latest_value(items, code)
            if val is not None:
                rates[name] = val
                found = True
        if found:
            source = "LIVE_TCMB"

    if not rates:
        rates = {
            "policy_rate":   42.50,
            "overnight_repo": 42.00,
            "tlref":          42.00,
        }

    return {
        "rates":        rates,
        "source":       source,
        "currency":     "TRY",
        "unit":         "percent_per_annum",
        "retrieved_at": _now(),
    }


# -----------------------------------------------------------------------
# Enflasyon
# -----------------------------------------------------------------------

def get_inflation_data(months: int = 12) -> dict:
    """TÜFE ve ÜFE verileri. EVDS3 veya mock fallback."""
    cfg = get_config()
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=months * 31)).strftime("%d-%m-%Y")
    end   = today.strftime("%d-%m-%Y")
    result: dict[str, Any] = {}
    source = "MOCK"

    if cfg.is_tcmb_configured():
        found = False
        for name, (code, formula) in SERIES_INFLATION.items():
            items = _evds3_fetch(code, start, end,
                                 cfg.tcmb_username or "", cfg.tcmb_password or "",
                                 cfg.http_timeout, formula=formula, frequency="5")
            # formula eklenince key: TP_XXX-<formula>
            alt_plain = code.replace(".", "_")
            alt_formula = f"{alt_plain}-{formula}"
            series = []
            for it in items:
                raw = it.get(code) or it.get(alt_plain) or it.get(alt_formula)
                if raw and raw not in ("", "ND"):
                    try:
                        series.append({"date": it["Tarih"],
                                       "value": float(str(raw).replace(",", ""))})
                    except (ValueError, TypeError):
                        pass
            if series:
                result[name] = series
                found = True
        if found:
            source = "LIVE_TCMB"

    if not result:
        result = {
            "cpi_annual": [{"date": "01-2026", "value": 39.05}],
            "ppi_annual": [{"date": "01-2026", "value": 22.11}],
        }

    return {"inflation": result, "source": source, "retrieved_at": _now()}


# -----------------------------------------------------------------------
# Herhangi bir EVDS3 serisi
# -----------------------------------------------------------------------

def get_evds_series(series_code: str,
                    start_date: str | None = None,
                    end_date: str | None = None,
                    days: int = 30) -> dict:
    """
    Herhangi bir EVDS3 seri kodunu çeker (TCMB_USERNAME + TCMB_PASSWORD gerekli).

    Örnek seriler:
      TP.DK.USD.A.YTL  — USD/TRY kuru (artık today.xml ile daha hızlı alınır)
      TP.TG2.Y01       — Politika faizi
      TP.FG.J0         — TÜFE aylık değişim
      TP.PA2.A         — M2 para arzı

    Tam liste: https://evds3.tcmb.gov.tr → Veri Grupları
    """
    cfg = get_config()
    if not cfg.is_tcmb_configured():
        return {
            "error":       "TCMB_USERNAME ve TCMB_PASSWORD tanımlı değil.",
            "series_code": series_code,
            "hint":        "evds3.tcmb.gov.tr adresinden ücretsiz kayıt olun, "
                           ".env'e TCMB_USERNAME ve TCMB_PASSWORD ekleyin.",
        }

    today = datetime.now(timezone.utc)
    start = start_date or (today - timedelta(days=days)).strftime("%d-%m-%Y")
    end   = end_date   or today.strftime("%d-%m-%Y")

    items = _evds3_fetch(series_code, start, end,
                         cfg.tcmb_username or "", cfg.tcmb_password or "",
                         cfg.http_timeout)
    if not items:
        return {
            "error":       f"Seri bulunamadı veya veri yok: {series_code}",
            "series_code": series_code,
            "start_date":  start,
            "end_date":    end,
        }

    alt = series_code.replace(".", "_")
    data_points = []
    for item in items:
        val = item.get(series_code) or item.get(alt)
        if val and val not in ("", None):
            data_points.append({"date": item.get("Tarih", ""), "value": float(val)})

    latest = data_points[-1]["value"] if data_points else None
    return {
        "series_code":  series_code,
        "source":       "LIVE_TCMB",
        "start_date":   start,
        "end_date":     end,
        "data_points":  data_points,
        "count":        len(data_points),
        "latest_value": latest,
        "retrieved_at": _now(),
    }


# -----------------------------------------------------------------------
# Market data (FX + BIST mock)
# -----------------------------------------------------------------------

def get_market_data(symbols: list[str], data_type: str = "realtime",
                    period: str | None = None) -> dict:
    """BIST endeksleri ve FX çiftleri. FX = TCMB today.xml, diğerleri mock."""
    data: dict[str, Any] = {}
    bist_base = {"BIST100": 9500, "BIST30": 9480, "XBANK": 5200,
                 "BRENTOIL": 72.5, "XAUUSD": 3040}

    fx_pairs = {"USDTRY", "EURTRY", "GBPTRY", "CHFTRY", "JPYTRY",
                "SARTRY", "AEDTRY", "AUDTRY", "CADTRY"}

    for sym in symbols:
        if sym in fx_pairs:
            base, quote = sym[:3], sym[3:]
            rd = get_fx_rate(base, quote)
            data[sym] = {
                "price":      rd["mid_rate"],
                "change_pct": round(random.uniform(-1.5, 1.5), 2),
                "source":     rd["source"],
                "volume":     random.randint(1_000_000, 500_000_000),
                "timestamp":  _now(),
            }
        else:
            base_price = bist_base.get(sym, 100)
            change_pct = round(random.uniform(-3, 3), 2)
            data[sym] = {
                "price":      round(base_price * (1 + change_pct / 100), 2),
                "change_pct": change_pct,
                "source":     "MOCK",
                "volume":     random.randint(100_000, 50_000_000),
                "timestamp":  _now(),
            }

    return {"data_type": data_type, "quotes": data, "source": "TCMB_XML+MOCK"}
