#!/usr/bin/env python3
"""Catálogos auditáveis e preços de referência para o roteador de modelos.

A lista pública não comprova autenticação, entitlement ou tarifa da conta. Este
módulo nunca invoca modelos nem lê/imprime credenciais. Artificial Analysis é
aceita somente por snapshot manual v1.5 validado; não há scraping nem API
presumida.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable

ZEN_URL = "https://opencode.ai/zen/v1/models"
GO_URL = "https://opencode.ai/zen/go/v1/models"
OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
AA_URL = "https://artificialanalysis.ai/agents/coding-agents"
AA_METRIC = "aa_coding_agent_index"
AA_VERSION = "1.5"
OMP_THINKING_VARIANTS = frozenset({"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto"})
CACHE_DIR = Path(os.environ.get("DEV_WORKFLOWS_MODEL_CACHE", "~/.cache/dev-workflows/model-catalog")).expanduser()

# Exact reviewed links only. A family/name resemblance is never a join key.
_CURATED: dict[tuple[str, str, str | None], tuple[str, str]] = {
    ("opencode", "glm-5.3", None): ("z-ai/glm-5.3", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode-go", "glm-5.3", None): ("z-ai/glm-5.3", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode", "gpt-6-luna", None): ("openai/gpt-6-luna", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode-go", "gpt-6-luna", None): ("openai/gpt-6-luna", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode", "gpt-6-sol", None): ("openai/gpt-6-sol", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode", "claude-opus-5-5", None): ("anthropic/claude-opus-5.5", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode", "kimi-k3", None): ("moonshotai/kimi-k3", "OpenRouter cross-reference reviewed against spec sample"),
    ("opencode-go", "kimi-k3", None): ("moonshotai/kimi-k3", "OpenRouter cross-reference reviewed against spec sample"),
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _secure_url(value: Any, hostname: str | None = None) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and (hostname is None or parsed.hostname in (hostname, "www." + hostname)) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment


def decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Valores monetários devem ser strings decimais ou inteiros, não float/bool")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"decimal inválido: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("decimal deve ser finito")
    return result


def decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _json_request(url: str, timeout: float = 20) -> tuple[Any, str, str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "dev-workflows-model-catalog/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        final_url = response.geturl()
    return json.loads(body), final_url, sha256(body)


def _unwrap_catalog(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        models = payload
    elif isinstance(payload, dict):
        models = next((payload[k] for k in ("data", "models", "items") if isinstance(payload.get(k), list)), None)
        if models is None:
            raise ValueError("formato de catálogo não reconhecido")
    else:
        raise ValueError("catálogo não é JSON de objetos")
    if any(not isinstance(item, dict) for item in models):
        raise ValueError("catálogo contém item não-objeto")
    return models


def parse_provider_catalog(payload: Any, provider: str, source_url: str, captured_at: str | None = None) -> list[dict[str, Any]]:
    """Converte catálogos Zen/Go sem sintetizar IDs ou variantes."""
    captured_at = captured_at or utc_now()
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for item in _unwrap_catalog(payload):
        raw_id = item.get("id") or item.get("model_id")
        if not isinstance(raw_id, str) or not raw_id.strip() or "/" in raw_id or "#" in raw_id:
            raise ValueError(f"ID inválido no catálogo {provider}")
        model_id = raw_id.strip()
        variants = item.get("variants")
        if variants is None:
            variants = [None]
        elif isinstance(variants, dict):
            variants = list(variants)
        if not isinstance(variants, list) or any(v is not None and (not isinstance(v, str) or not v) for v in variants):
            raise ValueError(f"variantes inválidas para {provider}/{model_id}")
        for variant in variants:
            key = (model_id, variant)
            if key in seen:
                continue
            seen.add(key)
            model_key = f"{provider}/{model_id}" + (f"#{variant}" if variant else "")
            result.append({
                "name": str(item.get("name") or model_id), "tool": "opencode", "provider": provider,
                "model_id": model_id, "variant": variant, "model_key": model_key,
                "context_length": item.get("context_length") or item.get("context_window"),
                "modalities": item.get("modalities"), "tool_calling": item.get("tool_calling"),
                "billing_mode": "zen_balance" if provider == "opencode" else "go_quota",
                "availability": {"listed": True, "authenticated": None, "entitled": None, "verified_at": None},
                "public_source": source_url, "captured_at": captured_at,
            })
    return result


_OR_PRICE_FIELDS = {
    "input": "prompt", "output": "completion", "cache_read": "input_cache_read",
    "cache_write": "input_cache_write", "cache_write_5m": "input_cache_write_5m",
    "cache_write_1h": "input_cache_write_1h", "cache_write_24h": "input_cache_write_24h",
}


def _public_context_tiers(overrides: Any, prices: dict[str, Any], source_url: str,
                          captured_at: str) -> list[dict[str, Any]]:
    if not isinstance(overrides, list):
        return []
    tiers = []
    for override in overrides:
        if not isinstance(override, dict):
            continue
        threshold = override.get("min_prompt_tokens")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0:
            continue
        tier_prices = dict(prices)
        for target, source in _OR_PRICE_FIELDS.items():
            if source in override:
                parsed = decimal_value(override[source])
                tier_prices[target] = decimal_text(parsed) if parsed is not None and parsed >= 0 else None
        tiers.append({"min_context_tokens": threshold, "price_per_token_usd": tier_prices,
                      "source_url": source_url, "captured_at": captured_at})
    return sorted(tiers, key=lambda tier: tier["min_context_tokens"])


def parse_openrouter(payload: Any, overrides: dict[str, Any] | None = None, source_url: str = OPENROUTER_URL,
                     captured_at: str | None = None) -> dict[str, dict[str, Any]]:
    """Preserva tarifas USD/token, variantes de cache e condições de preço."""
    captured_at = captured_at or utc_now()
    overrides = overrides or {}
    output = {}
    fields = _OR_PRICE_FIELDS
    for item in _unwrap_catalog(payload):
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id or any(char.isspace() for char in model_id):
            raise ValueError("OpenRouter contém ID inválido")
        if model_id in output:
            raise ValueError(f"ID OpenRouter duplicado: {model_id}")
        pricing = item.get("pricing") or {}
        if not isinstance(pricing, dict):
            raise ValueError(f"pricing inválido para {model_id}")
        prices = {}
        unsupported_prices = {}
        for target, source in fields.items():
            raw = pricing.get(source)
            price = decimal_value(raw) if raw is not None else None
            if price is not None and price < 0:
                unsupported_prices[target] = str(raw)
                price = None  # Credit/rebate is not a usable nonnegative cost estimate.
            prices[target] = decimal_text(price)
        base = {
            "id": model_id, "name": item.get("name"), "canonical_slug": item.get("canonical_slug"),
            "price_per_token_usd": prices, "price_unit": "USD/token",
            "display_usd_per_1m": {k: decimal_text(decimal_value(v) * Decimal(1_000_000)) if v is not None else None for k, v in prices.items()},
            "conditions": {
                "context_length": item.get("context_length"), "top_provider": item.get("top_provider"),
                "per_request_limits": item.get("per_request_limits"),
                "pricing_metadata": {k: v for k, v in pricing.items() if k not in fields.values()},
                "unsupported_negative_prices": unsupported_prices,
            },
            "source_url": source_url, "captured_at": captured_at, "source_hash": sha256(canonical_json(item)),
        }
        public_tiers = _public_context_tiers(pricing.get("overrides"), prices, source_url, captured_at)
        if public_tiers:
            base["conditions"]["context_tiers"] = public_tiers
        override = overrides.get(model_id)
        if override is not None:
            if not isinstance(override, dict):
                raise ValueError(f"override deve ser objeto: {model_id}")
            allowed = {"price_per_token_usd", "display_usd_per_1m", "context_length", "ttl", "endpoint",
                       "price_conditions", "context_tiers", "source_url", "captured_at"}
            if set(override) - allowed:
                raise ValueError(f"override contém campo não permitido: {model_id}")
            has_base_prices = "price_per_token_usd" in override or "display_usd_per_1m" in override
            if has_base_prices:
                if not _secure_url(override.get("source_url")) or _parse_utc(override.get("captured_at")) is None:
                    raise ValueError(f"override de preço exige source_url https e captured_at: {model_id}")
                base["source_url"], base["captured_at"] = override["source_url"], override["captured_at"]
            for unit_field, divisor in (("price_per_token_usd", Decimal(1)), ("display_usd_per_1m", Decimal(1_000_000))):
                if unit_field not in override:
                    continue
                override_prices = override[unit_field]
                if not isinstance(override_prices, dict):
                    raise ValueError(f"{unit_field} deve ser objeto: {model_id}")
                for key, value in override_prices.items():
                    if key not in prices:
                        raise ValueError(f"campo de tarifa desconhecido: {key}")
                    parsed = decimal_value(value)
                    if parsed is not None and parsed < 0:
                        raise ValueError(f"preço override negativo: {model_id}")
                    prices[key] = decimal_text(parsed / divisor) if parsed is not None else None
            for field in ("context_length", "ttl", "endpoint", "price_conditions"):
                if field in override:
                    base["conditions"][field] = override[field]
            if "endpoint" in override and not _secure_url(override["endpoint"]):
                raise ValueError(f"endpoint override deve ser HTTPS sem credenciais/query: {model_id}")
            if "context_tiers" in override:
                raw_tiers = override["context_tiers"]
                if not isinstance(raw_tiers, list):
                    raise ValueError(f"context_tiers deve ser lista: {model_id}")
                tiers = []
                thresholds = set()
                for tier in raw_tiers:
                    tier_fields = {"min_context_tokens", "price_per_token_usd", "source_url", "captured_at"}
                    if not isinstance(tier, dict) or set(tier) != tier_fields:
                        raise ValueError(f"context tier inválido: {model_id}")
                    threshold = tier["min_context_tokens"]
                    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0 or threshold in thresholds:
                        raise ValueError(f"limite de contexto inválido/duplicado: {model_id}")
                    thresholds.add(threshold)
                    if not _secure_url(tier["source_url"]) or _parse_utc(tier["captured_at"]) is None:
                        raise ValueError(f"context tier requer origem e data auditáveis: {model_id}")
                    tier_prices = tier["price_per_token_usd"]
                    if not isinstance(tier_prices, dict) or not tier_prices or set(tier_prices) - set(prices):
                        raise ValueError(f"tarifas do context tier inválidas: {model_id}")
                    normalized = dict(prices)
                    for key, value in tier_prices.items():
                        parsed = decimal_value(value)
                        if parsed is None or parsed < 0:
                            raise ValueError(f"tarifa de contexto inválida: {model_id}")
                        normalized[key] = decimal_text(parsed)
                    tiers.append({"min_context_tokens": threshold, "price_per_token_usd": normalized,
                                  "source_url": tier["source_url"], "captured_at": tier["captured_at"]})
                base["conditions"]["context_tiers"] = sorted(
                    tiers + base["conditions"].get("context_tiers", []),
                    key=lambda x: x["min_context_tokens"])
            base["override"] = {k: v for k, v in override.items() if k in allowed}
            base["price_per_token_usd"] = {k: decimal_text(decimal_value(v)) if v is not None else None for k, v in prices.items()}
            base["display_usd_per_1m"] = {
                k: decimal_text(decimal_value(v) * Decimal(1_000_000)) if v is not None else None
                for k, v in base["price_per_token_usd"].items()
            }
            base["source_hash"] = sha256(canonical_json({"api_model": item, "override": override}))
        output[model_id] = base
    if set(overrides) - set(output):
        raise ValueError("override refere ID OpenRouter ausente")
    return output


def openrouter_price_for_profile(record: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
    selected = dict(record)
    conditions = record.get("conditions") or {}
    tiers = conditions.get("context_tiers") or []
    context_raw = tokens.get("context_length", tokens.get("input"))
    context = decimal_value(context_raw) if context_raw is not None else None
    if context is not None and not tiers:
        metadata = conditions.get("pricing_metadata")
        if isinstance(metadata, dict):
            tiers = _public_context_tiers(metadata.get("overrides"), record["price_per_token_usd"],
                                          record["source_url"], record["captured_at"])
    if context is not None:
        matching = [tier for tier in tiers if Decimal(tier["min_context_tokens"]) <= context]
        if matching:
            tier = max(matching, key=lambda item: item["min_context_tokens"])
            selected["price_per_token_usd"] = tier["price_per_token_usd"]
            selected["source_url"] = tier["source_url"]
            selected["captured_at"] = tier["captured_at"]
            selected["applied_context_tier"] = tier["min_context_tokens"]
    return selected


def reference_cost(price_per_token_usd: dict[str, Any], tokens: dict[str, Any]) -> Decimal | None:
    """C_OR em USD; None se qualquer tarifa necessária ao perfil estiver ausente."""
    aliases = {"input": ("input", "prompt"), "output": ("output", "completion"),
               "cache_read": ("cache_read", "input_cache_read"), "cache_write": ("cache_write", "input_cache_write")}
    total = Decimal(0)
    for kind, names in aliases.items():
        raw_count = tokens.get(kind, 0)
        if isinstance(raw_count, bool) or isinstance(raw_count, float):
            raise ValueError("contagem de tokens deve ser inteiro ou decimal exato")
        count = Decimal(str(raw_count))
        if not count.is_finite() or count < 0:
            raise ValueError(f"contagem de tokens inválida: {kind}")
        if count == 0:
            continue
        names_for_cost = names
        if kind == "cache_write" and tokens.get("cache_write_ttl"):
            ttl = tokens["cache_write_ttl"]
            if ttl not in ("5m", "1h", "24h"):
                raise ValueError("cache_write_ttl precisa ser 5m, 1h ou 24h")
            names_for_cost = (f"cache_write_{ttl}", f"input_cache_write_{ttl}")
        raw_price = next((price_per_token_usd[name] for name in names_for_cost if name in price_per_token_usd), None)
        price = decimal_value(raw_price) if raw_price is not None else None
        if price is None:
            return None
        if price < 0:
            raise ValueError("preço por token não pode ser negativo")
        total += count * price
    return total


def validate_aa_snapshot(payload: Any) -> list[dict[str, Any]]:
    """Aceita exclusivamente export manual auditável do Coding Agent Index v1.5."""
    if not isinstance(payload, dict):
        raise ValueError("snapshot AA deve ser objeto")
    allowed_root = {"metric_id", "version", "ingestion", "terms_accepted", "source_url", "attribution", "captured_at", "records"}
    if set(payload) - allowed_root:
        raise ValueError("snapshot AA contém campo não permitido")
    if payload.get("metric_id") != AA_METRIC or str(payload.get("version")) != AA_VERSION:
        raise ValueError("somente aa_coding_agent_index v1.5 é aceito; índices não são intercambiáveis")
    if payload.get("ingestion") != "manual_audited" or payload.get("terms_accepted") is not True:
        raise ValueError("snapshot precisa ser importação manual consentida (terms_accepted=true)")
    source_url = payload.get("source_url")
    if not _secure_url(source_url, "artificialanalysis.ai"):
        raise ValueError("source_url oficial da Artificial Analysis é obrigatório")
    if not isinstance(payload.get("attribution"), str) or not payload["attribution"]:
        raise ValueError("atribuição AA obrigatória")
    captured_at = payload.get("captured_at")
    captured_time = _parse_utc(captured_at)
    if captured_time is None or captured_time > dt.datetime.now(dt.timezone.utc):
        raise ValueError("captured_at obrigatório, UTC/offset-aware e não futuro")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records deve ser lista")
    validated = []
    seen_keys: set[tuple[str, str, str | None]] = set()
    allowed_record = {"metric_id", "version", "provider", "model_id", "variant", "score", "agent", "harness",
                      "settings", "match_grade", "evidence_url", "components", "fallback", "effort", "reasoning", "configuration"}
    for record in records:
        if not isinstance(record, dict) or set(record) - allowed_record:
            raise ValueError("registro AA inválido ou contém campo não permitido")
        if record.get("metric_id", AA_METRIC) != AA_METRIC or str(record.get("version", AA_VERSION)) != AA_VERSION:
            raise ValueError("índice/versão diferente não pode ser misturado")
        provider, model_id = record.get("provider"), record.get("model_id")
        if not isinstance(provider, str) or not isinstance(model_id, str) or not model_id or "/" in model_id or "#" in model_id:
            raise ValueError("mapeamento provider/model_id exato obrigatório")
        variant = record.get("variant")
        if variant is not None and (not isinstance(variant, str) or not variant):
            raise ValueError("variante AA inválida")
        key = (provider, model_id, variant)
        if key in seen_keys:
            raise ValueError("benchmark inconsistente: modelo/variante duplicado no snapshot")
        seen_keys.add(key)
        score = decimal_value(record.get("score"))
        if score is None or score < 0 or score > 100:
            raise ValueError("score AA precisa estar no intervalo 0..100")
        grade = record.get("match_grade")
        if grade not in ("exact", "proxy"):
            raise ValueError("match_grade deve ser exact ou proxy, sem fuzzy match")
        for key in ("agent", "harness", "settings", "evidence_url"):
            if key not in record or record[key] in (None, ""):
                raise ValueError(f"campo de proveniência AA obrigatório: {key}")
        if not _secure_url(record["evidence_url"], "artificialanalysis.ai"):
            raise ValueError("evidence_url AA inválida")
        validated.append({
            **record, "metric_id": AA_METRIC, "version": AA_VERSION, "score": decimal_text(score),
            "source_url": source_url, "attribution": payload["attribution"], "observed_at": captured_at,
            "snapshot_hash": sha256(canonical_json(payload)),
        })
    return validated


def validate_availability_snapshot(payload: Any) -> dict[tuple[str, str, str | None], dict[str, Any]]:
    """Validates explicit account evidence without accepting or retaining secrets."""
    if not isinstance(payload, dict) or payload.get("tool") not in ("opencode", "omp") or payload.get("ingestion") != "manual_audited":
        raise ValueError("availability precisa ser snapshot manual auditado de opencode ou omp")
    tool = payload["tool"]
    if payload.get("user_confirmed") is not True:
        raise ValueError("snapshot de disponibilidade exige user_confirmed=true")
    captured_at = payload.get("captured_at")
    if not isinstance(captured_at, str):
        raise ValueError("captured_at de disponibilidade obrigatório")
    try:
        captured_dt = dt.datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("captured_at de disponibilidade inválido") from exc
    if captured_dt.tzinfo is None or captured_dt > dt.datetime.now(dt.timezone.utc):
        raise ValueError("captured_at precisa ser UTC/offset-aware e não futuro")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records de disponibilidade deve ser lista")
    result = {}
    source_hash = sha256(canonical_json(payload))
    allowed_fields = {"provider", "model_id", "variant", "local_listed", "authenticated", "entitled",
                      "verified_at", "source", "balance_confirmed", "balance_verified_at"}
    for record in records:
        if not isinstance(record, dict) or set(record) - allowed_fields:
            raise ValueError("snapshot de disponibilidade contém campos não permitidos")
        provider, model_id, variant = record.get("provider"), record.get("model_id"), record.get("variant")
        if not isinstance(provider, str) or not isinstance(model_id, str) or not model_id or "/" in model_id or "#" in model_id or (variant is not None and not isinstance(variant, str)):
            raise ValueError("provider/model_id/variant exatos são obrigatórios")
        if any(field not in record for field in ("local_listed", "authenticated", "entitled", "verified_at", "source")):
            raise ValueError("snapshot deve declarar todos os campos de disponibilidade")
        key = (provider, model_id, variant)
        if key in result:
            raise ValueError("snapshot de disponibilidade contém ID/variante duplicado")
        for field in ("local_listed", "authenticated", "entitled"):
            if record[field] is not None and not isinstance(record[field], bool):
                raise ValueError(f"{field} deve ser bool ou null")
        balance_confirmed = record.get("balance_confirmed")
        if balance_confirmed is not None and not isinstance(balance_confirmed, bool):
            raise ValueError("balance_confirmed deve ser bool ou null")
        balance_verified_at = record.get("balance_verified_at")
        balance_time = _parse_utc(balance_verified_at) if balance_verified_at else None
        if balance_time is not None and (balance_time > dt.datetime.now(dt.timezone.utc) or balance_confirmed is not True):
            raise ValueError("balance_verified_at requer confirmação explícita e não pode ser futuro")
        if balance_confirmed is True and balance_time is None:
            raise ValueError("saldo confirmado exige balance_verified_at UTC válido")
        verified_at = _parse_utc(record["verified_at"])
        if verified_at is None or verified_at > dt.datetime.now(dt.timezone.utc) or not isinstance(record["source"], str) or not record["source"]:
            raise ValueError("source e verified_at UTC válido são necessários para auditar a disponibilidade")
        result[key] = {
            "local_listed": record["local_listed"], "authenticated": record["authenticated"],
            "entitled": record["entitled"], "verified_at": record["verified_at"],
            "source": "manual_audited", "source_hash": source_hash,
            "balance_confirmed": balance_confirmed, "balance_verified_at": balance_verified_at,
        }
    return result



def validate_native_tariff_overrides(payload: Any) -> dict[str, dict[str, Any]]:
    """Valida cobrança nativa/quotas manuais; preços OpenRouter nunca são tarifa."""
    if not isinstance(payload, dict):
        raise ValueError("native_tariffs deve ser objeto JSON")
    result = {}
    allowed = {"billing_mode", "price_per_token_usd", "quota_window_remaining", "quota_window_debit",
               "use_balance_fallback", "source_url", "captured_at", "account_confirmed", "available_balance_usd"}
    for model_key, value in payload.items():
        if not isinstance(model_key, str) or not isinstance(value, dict) or set(value) - allowed:
            raise ValueError("override native contém estrutura/campo inválido")
        if value.get("account_confirmed") is not True:
            raise ValueError("tarifa/cota native exige confirmação explícita da conta")
        mode = value.get("billing_mode")
        if mode not in ("zen_balance", "go_quota", "omp_payg"):
            raise ValueError("billing_mode native inválido")
        if not _secure_url(value.get("source_url")):
            raise ValueError("source_url HTTPS de tarifa/cota native obrigatório")
        captured_at = value.get("captured_at")
        try:
            captured = dt.datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("captured_at de tarifa/cota native inválido") from exc
        if captured.tzinfo is None or captured > dt.datetime.now(dt.timezone.utc):
            raise ValueError("captured_at de tarifa/cota native precisa ser aware e não futuro")
        record = {k: value[k] for k in ("billing_mode", "source_url", "captured_at", "account_confirmed")}
        if mode in ("zen_balance", "omp_payg"):
            rates = value.get("price_per_token_usd")
            if not isinstance(rates, dict) or not rates:
                raise ValueError("tarifa nativa precisa de price_per_token_usd")
            record["price_per_token_usd"] = {
                k: decimal_text(decimal_value(v)) for k, v in rates.items()
                if k in ("input", "output", "cache_read", "cache_write", "cache_write_5m", "cache_write_1h", "cache_write_24h")
            }
            if len(record["price_per_token_usd"]) != len(rates) or any(v is None or Decimal(v) < 0 for v in record["price_per_token_usd"].values()):
                raise ValueError("componentes de tarifa nativa inválidos")
            balance = decimal_value(value.get("available_balance_usd"))
            if balance is None or balance < 0:
                raise ValueError("Zen/OMP payg exige saldo disponível confirmado")
            record["available_balance_usd"] = decimal_text(balance)
        else:
            remaining, debit = value.get("quota_window_remaining"), value.get("quota_window_debit")
            if not isinstance(remaining, dict) or not isinstance(debit, dict) or any(k not in remaining or k not in debit for k in ("5h", "weekly", "monthly")):
                raise ValueError("cota Go exige valores por modelo em 5h/weekly/monthly")
            record["quota_window_remaining"] = {k: decimal_text(decimal_value(remaining[k])) for k in ("5h", "weekly", "monthly")}
            record["quota_window_debit"] = {k: decimal_text(decimal_value(debit[k])) for k in ("5h", "weekly", "monthly")}
            if any(record[key][window] is None or Decimal(record[key][window]) < 0 for key in ("quota_window_remaining", "quota_window_debit") for window in ("5h", "weekly", "monthly")):
                raise ValueError("quota Go precisa ter todos os valores decimais não negativos")
            fallback = value.get("use_balance_fallback", False)
            if not isinstance(fallback, bool):
                raise ValueError("use_balance_fallback precisa ser bool")
            record["use_balance_fallback"] = fallback
        result[model_key] = record
    return result

def discover_local_models(provider: str, executable: str = "opencode", runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Lista IDs pela CLI sem persistir stdout bruto, stderr, environment ou credenciais."""
    try:
        result = runner([executable, "models", provider, "--refresh"], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "models": [], "reason": "cli_local_indisponivel"}
    if result.returncode != 0:
        return {"ok": False, "models": [], "reason": "descoberta_local_falhou"}
    found: set[str] = set()
    # Apenas linhas integralmente compostas por um ID de modelo permitido.
    for line in result.stdout.splitlines():
        candidate = line.strip().strip("`'\" ")
        if candidate.startswith(provider + "/"):
            candidate = candidate[len(provider) + 1:]
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:+/-]*(?:#[A-Za-z0-9._+-]+)?", candidate):
            if " " not in candidate and not candidate.startswith("-"):
                found.add(candidate)
    return {"ok": True, "models": sorted(found), "reason": None}


def parse_omp_models(payload: Any, provider: str, captured_at: str | None = None) -> list[dict[str, Any]]:
    """Converte a listagem JSON local do OMP; ela prova listagem, nunca entitlement."""
    captured_at = captured_at or utc_now()
    if isinstance(payload, list):
        models = payload
    elif isinstance(payload, dict):
        models = next((payload[key] for key in ("models", "data", "items") if isinstance(payload.get(key), list)), None)
        if models is None:
            raise ValueError("formato de listagem OMP não reconhecido")
    else:
        raise ValueError("listagem OMP não é JSON de modelos")
    if any(not isinstance(item, dict) for item in models):
        raise ValueError("listagem OMP contém modelo não-objeto")
    rows = []
    seen: set[tuple[str, str | None]] = set()
    for item in models:
        item_provider = item.get("provider", provider)
        raw_id = item.get("id") or item.get("model_id") or item.get("model")
        if not isinstance(item_provider, str) or item_provider != provider or not isinstance(raw_id, str):
            raise ValueError("provider e ID exatos são obrigatórios na listagem OMP")
        model_id = raw_id
        selector = item.get("selector")
        if selector is not None:
            if not isinstance(selector, str) or not selector.startswith(provider + "/") or selector[len(provider) + 1:] != model_id:
                raise ValueError("selector OMP qualificado diverge do provider/ID")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:+/-]*", model_id):
            raise ValueError("ID inválido na listagem OMP")
        thinking = item.get("thinking")
        if thinking is not None and (not isinstance(thinking, list) or any(
                not isinstance(level, str) or level not in OMP_THINKING_VARIANTS for level in thinking)):
            raise ValueError("níveis de thinking inválidos na listagem OMP")
        key = (model_id, None)
        if key in seen:
            continue
        seen.add(key)
        model_key = f"{provider}/{model_id}"
        rows.append({
            "name": model_id, "tool": "omp", "provider": provider, "model_id": model_id,
            "variant": None, "thinking": thinking, "model_key": model_key, "context_length": None,
            "modalities": None, "tool_calling": None, "billing_mode": "unknown",
            "availability": {"listed": True, "authenticated": None, "entitled": None, "verified_at": None},
            "public_source": "omp models --json (listagem local)", "captured_at": captured_at,
        })
    return rows


def discover_omp_models(provider: str, executable: str = "omp",
                        runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Lê IDs OMP localmente e descarta stdout/stderr brutos e dados de conta."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", provider):
        return {"ok": False, "models": [], "reason": "provider_omp_invalido"}
    try:
        result = runner([executable, "models", provider, "--json"], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "models": [], "reason": "cli_omp_indisponivel"}
    if result.returncode != 0 or not isinstance(result.stdout, str):
        return {"ok": False, "models": [], "reason": "listagem_omp_indisponivel"}
    try:
        payload = json.loads(result.stdout)
        rows = parse_omp_models(payload, provider)
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "models": [], "reason": "listagem_omp_invalida"}
    selectors = {row["model_key"] for row in rows}
    for row in rows:
        if row.get("variant") is None and isinstance(row.get("thinking"), list):
            selectors.update(f'{row["provider"]}/{row["model_id"]}#{level}' for level in row["thinking"])
    return {
        "ok": True, "models": sorted(selectors), "rows": rows,
        "source_hash": sha256(result.stdout.encode("utf-8")), "verified_at": utc_now(), "reason": None,
    }


def curated_mapping(provider: str, model_id: str, variant: str | None = None) -> dict[str, str] | None:
    match = _CURATED.get((provider, model_id, variant))
    if match is None:
        return None
    return {"openrouter_id": match[0], "provenance": match[1], "match_method": "exact_curated"}


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _read_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return default


def _http_fetch(url: str) -> tuple[Any, str, str]:
    return _json_request(url)


def sync(tool: str = "opencode", providers: Iterable[str] | None = None,
         cache_dir: str | Path | None = None, fetcher: Callable[[str], tuple[Any, str, str]] = _http_fetch,
         local_discoverer: Callable[[str], dict[str, Any]] = discover_local_models,
         aa_snapshot: str | Path | None = None, price_overrides: str | Path | None = None,
         availability_snapshot: str | Path | None = None,
         omp_discoverer: Callable[[str], dict[str, Any]] = discover_omp_models) -> dict[str, Any]:
    """Atualiza catálogos; listas OMP são locais e nunca provam entitlement."""
    if tool not in ("opencode", "omp"):
        raise ValueError("sync público/local suportado apenas para opencode ou omp")
    cache = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    requested = tuple(dict.fromkeys(providers if providers is not None else
                                    (() if tool == "omp" else ("opencode", "opencode-go"))))
    if tool == "omp":
        if not requested:
            raise ValueError("OMP exige providers explicitamente autorizados")
        if any(not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", provider) for provider in requested):
            raise ValueError("provider OMP inválido")
        provider_urls = {}
    else:
        provider_urls = {"opencode": ZEN_URL, "opencode-go": GO_URL}
        if not requested or any(provider not in provider_urls for provider in requested):
            raise ValueError("provider desconhecido; use opencode,opencode-go")
    source_hashes: dict[str, str] = {}
    override_bytes = Path(price_overrides).read_bytes() if price_overrides else b""
    override_data = json.loads(override_bytes) if override_bytes else {}
    if not isinstance(override_data, dict):
        raise ValueError("arquivo de overrides deve ser objeto JSON")
    reserved = {"openrouter", "native_tariffs"}
    or_overrides = override_data.get("openrouter", {k: v for k, v in override_data.items() if k not in reserved})
    native_overrides = validate_native_tariff_overrides(override_data.get("native_tariffs", {}))
    if override_bytes:
        source_hashes["overrides"] = sha256(override_bytes)
    if not isinstance(or_overrides, dict):
        raise ValueError("overrides OpenRouter deve ser objeto")
    availability_map: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    if availability_snapshot:
        availability_bytes = Path(availability_snapshot).read_bytes()
        availability_payload = json.loads(availability_bytes)
        if not isinstance(availability_payload, dict) or availability_payload.get("tool") != tool:
            raise ValueError("tool do snapshot de disponibilidade diverge do catálogo")
        availability_map = validate_availability_snapshot(availability_payload)
        source_hashes["availability"] = sha256(availability_bytes)

    catalog_rows = []
    captured = utc_now()
    if aa_snapshot:
        snapshot_bytes = Path(aa_snapshot).read_bytes()
        aa_payload = json.loads(snapshot_bytes)
        aa_records = validate_aa_snapshot(aa_payload)
        _atomic_json(cache / f"aa-{AA_METRIC}-v{AA_VERSION}.json", {
            "metric_id": AA_METRIC, "version": AA_VERSION, "captured_at": aa_payload["captured_at"],
            "source_hash": sha256(snapshot_bytes), "records": aa_records,
        })
        source_hashes["aa"] = sha256(snapshot_bytes)
    aa_stored = _read_json(cache / f"aa-{AA_METRIC}-v{AA_VERSION}.json", {"records": []})
    scores = aa_stored.get("records", []) if isinstance(aa_stored, dict) else []
    scores_by_key = {(r.get("provider"), r.get("model_id"), r.get("variant")): r for r in scores}

    if tool == "opencode":
        for provider in requested:
            payload, source_url, digest = fetcher(provider_urls[provider])
            catalog_rows.extend(parse_provider_catalog(payload, provider, source_url, captured))
            source_hashes[provider] = digest
        local_result = {p: local_discoverer(p) for p in requested}
    else:
        local_result = {p: omp_discoverer(p) for p in requested}
        for provider, result in local_result.items():
            if result.get("ok"):
                catalog_rows.extend(result.get("rows", []))
                source_hashes[provider] = result["source_hash"]

    if tool == "omp":
        base_rows = {(row["provider"], row["model_id"]): row for row in catalog_rows if row.get("variant") is None}
        present = {row["model_key"] for row in catalog_rows}
        for (provider, model_id, variant), _score in scores_by_key.items():
            base_key = f"{provider}/{model_id}"
            model_key = base_key + (f"#{variant}" if variant else "")
            supported = base_rows.get((provider, model_id), {}).get("thinking")
            if (variant not in OMP_THINKING_VARIANTS or model_key in present or
                    not isinstance(supported, list) or variant not in supported or
                    base_key not in local_result.get(provider, {}).get("models", [])):
                continue
            base = base_rows.get((provider, model_id))
            if base is None:
                continue
            variant_row = dict(base)
            variant_row["variant"] = variant
            variant_row["model_key"] = model_key
            variant_row["availability"] = dict(base.get("availability") or {})
            catalog_rows.append(variant_row)
            present.add(model_key)

    applied_availability = set()
    for row in catalog_rows:
        provider = row["provider"]
        local = local_result.get(provider, {"ok": False, "models": []})
        local_ids = set(local.get("models", [])) if local.get("ok") else set()
        catalog_key = (provider, row["model_id"], row.get("variant"))
        manual = availability_map.get(catalog_key)
        if manual:
            applied_availability.add(catalog_key)
        if tool == "omp":
            local_listed = row["model_key"] in local_ids if local.get("ok") else None
        else:
            local_key = row["model_id"] + (f"#{row['variant']}" if row.get("variant") else "")
            local_listed = local_key in local_ids if local.get("ok") else None
        if manual and local.get("ok"):
            local_listed = local_listed is True and manual["local_listed"] is True
        row["availability"].update({
            "local_listed": local_listed,
            "authenticated": manual["authenticated"] if manual else None,
            "entitled": manual["entitled"] if manual else None,
            "verified_at": manual["verified_at"] if manual else (captured if local.get("ok") else None),
            "local_verified_at": local.get("verified_at", captured) if local.get("ok") else None,
            "account_verified_at": manual["verified_at"] if manual else None,
            "balance_confirmed": manual.get("balance_confirmed") if manual else None,
            "balance_verified_at": manual.get("balance_verified_at") if manual else None,
            "source": "manual_audited" if manual else ("omp_models_cli" if tool == "omp" and local.get("ok") else "opencode_models_cli" if local.get("ok") else None),
            "evidence_hash": manual["source_hash"] if manual else None,
        })
        if local_listed is not True:
            row["availability_reason"] = "nao_listado_localmente" if local.get("ok") else local.get("reason", "verificacao_local_indisponivel")
        elif manual is None:
            row["availability_reason"] = "conta_nao_verificada"
        elif manual["authenticated"] is not True:
            row["availability_reason"] = "autenticacao_nao_confirmada"
        elif manual["entitled"] is not True:
            row["availability_reason"] = "entitlement_nao_confirmado"
        else:
            row["availability_reason"] = None
        row["source_hash"] = source_hashes.get(provider)
        row["mapping"] = curated_mapping(provider, row["model_id"], row.get("variant"))
        native = native_overrides.get(row["model_key"])
        if native:
            if tool == "opencode" and native["billing_mode"] != row["billing_mode"]:
                raise ValueError("billing_mode do override diverge do provider publicado")
            if tool != "omp" and native["billing_mode"] == "omp_payg":
                raise ValueError("OMP payg não pode ser roteado por outra ferramenta")
            row["billing_mode"] = native["billing_mode"]
            tariff_fields = ("billing_mode", "source_url", "captured_at", "account_confirmed",
                             "price_per_token_usd", "available_balance_usd")
            row["native_tariff"] = {k: native[k] for k in tariff_fields if k in native}
            if native["billing_mode"] == "go_quota":
                row["quota_window_remaining"] = native["quota_window_remaining"]
                row["quota_window_debit"] = native["quota_window_debit"]
                row["quota_verified_at"] = native["captured_at"]
                row["quota_source_url"] = native["source_url"]
                row["use_balance_fallback"] = native["use_balance_fallback"]
    invalid_availability = {key for key in set(availability_map) - applied_availability if key[0] in requested}
    if invalid_availability:
        raise ValueError("snapshot de disponibilidade referencia modelo/variante fora da listagem local")
    invalid_native = {key for key in native_overrides if key not in {r["model_key"] for r in catalog_rows}}
    if invalid_native:
        raise ValueError("tarifa native referencia modelo/variante fora do catálogo")

    prices_payload, price_url, price_hash = fetcher(OPENROUTER_URL)
    prices = parse_openrouter(prices_payload, or_overrides, price_url, captured)
    source_hashes["openrouter"] = price_hash
    for row in catalog_rows:
        row["score"] = scores_by_key.get((row["provider"], row["model_id"], row.get("variant")))
        mapping = row.get("mapping")
        price_id = mapping["openrouter_id"] if mapping else None
        row["openrouter"] = prices.get(price_id) if price_id else None
        row["or_price_per_token"] = row["openrouter"]["price_per_token_usd"] if row["openrouter"] else {"input": None, "output": None, "cache_read": None, "cache_write": None}
        row["price_conditions"] = row["openrouter"]["conditions"] if row["openrouter"] else None
    snapshot = {"schema_version": 1, "tool": tool, "captured_at": captured, "source_hashes": source_hashes,
                "providers": list(requested), "models": catalog_rows, "openrouter": prices,
                "benchmark": {"metric_id": AA_METRIC, "version": AA_VERSION, "records": scores}}
    snapshot["snapshot_hash"] = sha256(canonical_json({k: v for k, v in snapshot.items() if k != "snapshot_hash"}))
    _atomic_json(cache / f"catalog-{tool}.json", snapshot)
    return {
        "tool": tool, "model_count": len(catalog_rows), "provider_count": len(requested),
        "local_discovery": {p: {"ok": v["ok"], "count": len(v["models"]), "reason": v.get("reason")}
                            for p, v in local_result.items()},
        "snapshot_hash": snapshot["snapshot_hash"], "captured_at": captured, "source_hashes": source_hashes,
    }


def load_snapshot(tool: str = "opencode", cache_dir: str | Path | None = None) -> dict[str, Any] | None:
    cache = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    snapshot = _read_json(cache / f"catalog-{tool}.json", None)
    return snapshot if isinstance(snapshot, dict) else None


def band_for_score(score: Any) -> str | None:
    value = decimal_value(score)
    if value is None:
        return None
    if Decimal(10) <= value < Decimal(20):
        return "leve"
    if Decimal(20) <= value < Decimal(50):
        return "media"
    if Decimal(50) <= value <= Decimal(100):
        return "alta"
    return None


def list_models(tool: str = "opencode", cache_dir: str | Path | None = None, show_missing: bool = True,
                as_of_utc: str | None = None) -> list[dict[str, Any]]:
    snapshot = load_snapshot(tool, cache_dir)
    if snapshot is None:
        return []
    now = _parse_utc(as_of_utc) if as_of_utc is not None else dt.datetime.now(dt.timezone.utc)
    if now is None:
        raise ValueError("as_of_utc deve ser data/hora UTC ISO 8601")
    result = []
    for model in snapshot.get("models", []):
        score = model.get("score") or {}
        price = model.get("or_price_per_token") or {}
        availability = model.get("availability") or {}
        local_listed = availability.get("local_listed")
        if not show_missing and local_listed is not True:
            continue
        display = model.get("openrouter", {}).get("display_usd_per_1m", {}) if model.get("openrouter") else {}
        stale_reasons = []
        or_snapshot = model.get("openrouter") or {}
        price_time = _parse_utc(or_snapshot.get("captured_at")) if or_snapshot else None
        if price_time is None:
            stale_reasons.append("preco_referencial_ausente")
        elif now - price_time > dt.timedelta(hours=24):
            stale_reasons.append("preco_referencial_obsoleto")
        if score:
            score_time = _parse_utc(score.get("observed_at"))
            if score_time is None or now - score_time > dt.timedelta(days=30):
                stale_reasons.append("benchmark_obsoleto")
        local_time = _parse_utc(availability.get("verified_at"))
        if local_listed is True and (local_time is None or now - local_time > dt.timedelta(hours=24)):
            stale_reasons.append("descoberta_local_precisa_revalidacao")
        account_available = True if all(availability.get(k) is True for k in ("local_listed", "authenticated", "entitled")) else (False if any(availability.get(k) is False for k in ("local_listed", "authenticated", "entitled")) else "n/d")
        native_or_quota = model.get("native_tariff") or "n/d"
        if model.get("billing_mode") == "go_quota" and isinstance(native_or_quota, dict):
            native_or_quota = {
                **native_or_quota,
                "quota_window_remaining": model.get("quota_window_remaining"),
                "quota_window_debit": model.get("quota_window_debit"),
                "use_balance_fallback": model.get("use_balance_fallback"),
            }
        result.append({
            "nome": model.get("name") or "n/d", "tool": model.get("tool") or "n/d", "model_key": model.get("model_key") or "n/d",
            "openrouter_id": model.get("mapping", {}).get("openrouter_id") if model.get("mapping") else "n/d",
            "preco_or_entrada_usd_1m": display.get("input") if display.get("input") is not None else "n/d",
            "preco_or_saida_usd_1m": display.get("output") if display.get("output") is not None else "n/d",
            "preco_or_cache_leitura_usd_1m": display.get("cache_read") if display.get("cache_read") is not None else "n/d",
            "preco_or_cache_escrita_usd_1m": display.get("cache_write") if display.get("cache_write") is not None else "n/d",
            "preco_or_cache_escrita_1h_usd_1m": display.get("cache_write_1h") if display.get("cache_write_1h") is not None else "n/d",
            "condicao_de_preco": model.get("price_conditions") or "n/d", "coding_index_versao": score.get("version") or "n/d",
            "coding_index_nota": score.get("score") or "n/d", "benchmark_por_componente_se_publicado": score.get("components") or "n/d",
            "harness_aa": score.get("harness") or "n/d", "reasoning_aa": score.get("settings") or "n/d",
            "grau_do_match": score.get("match_grade") or "n/d", "faixa": band_for_score(score.get("score")) or "n/d",
            "preco_native_ou_cota": native_or_quota,
            "disponivel_na_conta": account_available,
            "motivo_da_exclusao": model.get("availability_reason") or ("sem_score_compatível" if not score else "n/d"),
            "fonte": {"catalog": model.get("public_source"), "benchmark": score.get("source_url"), "openrouter": or_snapshot.get("source_url")},
            "capturado_em": model.get("captured_at") or "n/d", "stale": bool(stale_reasons), "stale_reasons": stale_reasons,
            "availability": availability, "billing_mode": model.get("billing_mode") or "n/d",
            "source_hash": model.get("source_hash") or "n/d", "or_price_per_token": price, "score": score or "n/d",
        })
    return sorted(result, key=lambda r: (r.get("tool") or "", r.get("model_key") or ""))


def _parse_utc(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        return None
    return result.astimezone(dt.timezone.utc)


def coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        provider = row.get("model_key", "n/d").split("/", 1)[0]
        band = row.get("faixa", "n/d")
        group = counts.setdefault(f"{provider}/{band}", {"scored": 0, "total": 0})
        group["total"] += 1
        group["scored"] += row.get("coding_index_nota") != "n/d"
    return counts


LIST_FIELDS = (
    "nome", "tool", "model_key", "openrouter_id", "preco_or_entrada_usd_1m", "preco_or_saida_usd_1m",
    "preco_or_cache_leitura_usd_1m", "preco_or_cache_escrita_usd_1m", "preco_or_cache_escrita_1h_usd_1m", "condicao_de_preco",
    "coding_index_versao", "coding_index_nota", "benchmark_por_componente_se_publicado", "harness_aa",
    "reasoning_aa", "grau_do_match", "faixa", "preco_native_ou_cota", "disponivel_na_conta",
    "motivo_da_exclusao", "fonte", "capturado_em", "stale", "stale_reasons", "availability",
    "billing_mode", "source_hash", "or_price_per_token", "score",
)


def _csv_text(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=LIST_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else ("n/d" if v is None else v) for k, v in row.items()})
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--tool", choices=("opencode", "omp"), default="opencode")
    p_sync.add_argument("--providers")
    p_sync.add_argument("--aa-snapshot")
    p_sync.add_argument("--price-overrides")
    p_sync.add_argument("--availability-snapshot")
    p_sync.add_argument("--cache-dir")
    p_list = sub.add_parser("list")
    p_list.add_argument("--tool", choices=("opencode", "claude", "omp"), default="opencode")
    p_list.add_argument("--show-missing", action="store_true", default=True)
    p_list.add_argument("--format", choices=("json", "csv"), default="json")
    p_list.add_argument("--as-of-utc", help="instante UTC ISO 8601 para reproduzir staleness arquivado")
    p_list.add_argument("--cache-dir")
    p_route = sub.add_parser("route")
    p_route.add_argument("--tool", choices=("opencode", "claude", "omp"), default="opencode")
    p_route.add_argument("--role", required=True)
    p_route.add_argument("--providers", help="providers explicitamente autorizados, separados por vírgula")
    p_route.add_argument("--format", choices=("json",), default="json")
    p_route.add_argument("--tokens", default="{}", help="perfil JSON de tokens por tarefa")
    p_route.add_argument("--budget-usd")
    p_route.add_argument("--allow-proxy-score", "--allow-proxy", dest="allow_proxy", action="store_true")
    p_route.add_argument("--max-loss-points", "--delta-points", dest="delta_points")
    p_route.add_argument("--max-price-age-hours", default="24")
    p_route.add_argument("--max-score-age-days", default="30")
    p_route.add_argument("--benchmark-metric", default="aa_coding_agent_index_v1.5")
    p_route.add_argument("--band", choices=("leve", "media", "alta"))
    p_route.add_argument("--bands-json")
    p_route.add_argument("--explain", action="store_true")
    p_route.add_argument("--cache-dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            providers = tuple(x for x in args.providers.split(",") if x) if args.providers else None
            data = sync(args.tool, providers, args.cache_dir, aa_snapshot=args.aa_snapshot,
                        price_overrides=args.price_overrides, availability_snapshot=args.availability_snapshot)
            print(json.dumps({"ok": True, "command": "sync", "data": data}, ensure_ascii=False))
        elif args.command == "list":
            rows = list_models(args.tool, args.cache_dir, show_missing=args.show_missing, as_of_utc=args.as_of_utc)
            if args.format == "csv":
                print(_csv_text(rows), end="")
            else:
                print(json.dumps({"ok": True, "command": "list", "snapshot_available": load_snapshot(args.tool, args.cache_dir) is not None,
                                  "coverage": coverage(rows), "models": rows}, ensure_ascii=False))
        else:
            from model_router import route_from_catalog
            token_profile = json.loads(args.tokens)
            if not isinstance(token_profile, dict):
                raise ValueError("--tokens deve ser objeto JSON")
            bands = json.loads(args.bands_json) if args.bands_json else None
            if bands is not None and not isinstance(bands, dict):
                raise ValueError("--bands-json deve ser objeto JSON")
            result = route_from_catalog(args.tool, args.role, args.providers.split(",") if args.providers else [],
                                        args.cache_dir, explain=args.explain, tokens=token_profile,
                                        budget_usd=args.budget_usd, allow_proxy=args.allow_proxy,
                                        delta_points=args.delta_points, max_price_age_hours=args.max_price_age_hours,
                                        max_score_age_days=args.max_score_age_days, band_override=args.band, bands=bands,
                                        benchmark_metric=args.benchmark_metric)
            print(json.dumps({"ok": result["selected"] is not None, **result}, ensure_ascii=False))
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "command": args.command, "error": {"code": type(exc).__name__, "message": "operação indisponível; consulte o snapshot local e a origem configurada"}}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
