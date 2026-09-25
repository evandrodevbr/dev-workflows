#!/usr/bin/env python3
"""Seleção conservadora por papel; custos OpenRouter nunca são tarifa de cobrança."""
from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from model_catalog import (AA_METRIC, AA_VERSION, CACHE_DIR, decimal_text, decimal_value, discover_local_models,
                           load_snapshot, openrouter_price_for_profile, reference_cost)

ROLE_BANDS = {
    "explorer": "leve", "verifier": "leve", "summarizer": "leve",
    "implementer": "media", "ui-critic": "media",
    "planner": "alta", "reviewer": "alta", "security-auditor": "alta",
}
DEFAULT_DELTA = {"leve": Decimal(3), "media": Decimal(3), "alta": Decimal(2)}
EXPECTED_HARNESSES = {"opencode": "OpenCode", "omp": "OMP", "claude": "Claude Code"}
WINDOWS = ("5h", "weekly", "monthly")
FIXED_BANDS = {
    "leve": (Decimal(10), Decimal(20)),
    "media": (Decimal(20), Decimal(50)),
    "alta": (Decimal(50), Decimal(100)),
}


def validate_bands(bands: dict[str, Any] | None) -> dict[str, tuple[Decimal, Decimal]]:
    """Aceita a configuração declarativa apenas se preservar as faixas normativas."""
    if bands is None:
        return FIXED_BANDS.copy()
    if not isinstance(bands, dict) or set(bands) != set(FIXED_BANDS):
        raise ValueError("bands deve conter exatamente leve/media/alta")
    normalized = {}
    for name, limits in bands.items():
        if not isinstance(limits, (list, tuple)) or len(limits) != 2:
            raise ValueError(f"faixa {name} deve declarar dois limites")
        low, high = (_decimal(value) for value in limits)
        if low is None or high is None:
            raise ValueError(f"limites da faixa {name} devem ser decimais")
        normalized[name] = (low, high)
    if normalized != FIXED_BANDS:
        raise ValueError("bands customizadas são recusadas; use 10..20, 20..50 e 50..100")
    return normalized


def _score_band(score: Decimal | None, bands: dict[str, tuple[Decimal, Decimal]]) -> str | None:
    if score is None:
        return None
    for name in ("leve", "media"):
        low, high = bands[name]
        if low <= score < high:
            return name
    low, high = bands["alta"]
    return "alta" if low <= score <= high else None


def _time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        return None
    return result.astimezone(dt.timezone.utc)


def _decimal(value: Any) -> Decimal | None:
    try:
        return decimal_value(value)
    except ValueError:
        return None


def _has_token_profile(tokens: dict[str, Any]) -> bool:
    return any((_decimal(tokens.get(key)) or Decimal(0)) > 0 for key in ("input", "output", "cache_read", "cache_write"))


def _staleness(row: dict[str, Any], now: dt.datetime, max_price_age_hours: Decimal, max_score_age_days: Decimal,
               tokens: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    mode = row.get("billing_mode")
    paid = mode in ("zen_balance", "go_quota", "omp_payg", "claude_subscription")
    price_record = row.get("openrouter") or {"price_per_token_usd": row.get("or_price_per_token") or {}}
    price = openrouter_price_for_profile(price_record, tokens)
    native = row.get("native_tariff") or {}
    has_reference_price = any(price.get("price_per_token_usd", {}).get(k) is not None
                              for k in ("input", "output", "cache_read", "cache_write"))
    if paid:
        if has_reference_price:
            price_time = _time(price.get("captured_at"))
            if price_time is None or price_time > now or (now - price_time).total_seconds() > float(max_price_age_hours * Decimal(3600)):
                reasons.append("preco_referencial_obsoleto_ou_ausente")
        score = row.get("score") or {}
        score_time = _time(score.get("observed_at"))
        if score_time is None or score_time > now or (now - score_time).total_seconds() > float(max_score_age_days * Decimal(86400)):
            reasons.append("benchmark_obsoleto_ou_ausente")
        if mode in ("zen_balance", "omp_payg"):
            native_time = _time(native.get("captured_at"))
            if native.get("account_confirmed") is not True or not str(native.get("source_url", "")).startswith("https://") or native_time is None or native_time > now or now - native_time > dt.timedelta(hours=float(max_price_age_hours)):
                reasons.append("tarifa_nativa_obsoleta_ou_nao_confirmada")
        if mode == "go_quota":
            quota_time = _time(row.get("quota_verified_at"))
            if quota_time is None or quota_time > now or now - quota_time > dt.timedelta(seconds=60) or not str(row.get("quota_source_url", "")).startswith("https://"):
                reasons.append("quota_go_obsoleta_ou_nao_confirmada")
        availability = row.get("availability") or {}
        local_time = _time(availability.get("local_verified_at") or availability.get("verified_at"))
        if local_time is None or local_time > now or now - local_time > dt.timedelta(hours=24):
            reasons.append("disponibilidade_local_precisa_revalidacao")
        account_time = _time(availability.get("account_verified_at"))
        if availability.get("authenticated") is True and availability.get("entitled") is True:
            if account_time is None or account_time > now or now - account_time > dt.timedelta(hours=24):
                reasons.append("entitlement_precisa_revalidacao")
        if mode in ("zen_balance", "omp_payg"):
            balance_time = _time(availability.get("balance_verified_at"))
            if availability.get("balance_confirmed") is not True or balance_time is None or balance_time > now or now - balance_time > dt.timedelta(seconds=60):
                reasons.append("saldo_nao_confirmado_ou_obsoleto")
    return reasons


def _profile_cost(row: dict[str, Any], tokens: dict[str, Any]) -> Decimal | None:
    record = row.get("openrouter") or {"price_per_token_usd": row.get("or_price_per_token") or {}}
    profile = openrouter_price_for_profile(record, tokens)
    return reference_cost(profile.get("price_per_token_usd") or {}, tokens)


def _native_cost_and_headroom(row: dict[str, Any], tokens: dict[str, Any]) -> tuple[Decimal | None, Decimal | None, str | None]:
    mode = row.get("billing_mode")
    native = row.get("native_tariff")
    if mode in ("zen_balance", "omp_payg"):
        if not _has_token_profile(tokens):
            return None, None, "perfil_tokens_native_nao_configurado"
        if not isinstance(native, dict) or not isinstance(native.get("price_per_token_usd"), dict) or native.get("account_confirmed") is not True:
            return None, None, "tarifa_native_nao_confirmada"
        amount = reference_cost(native["price_per_token_usd"], tokens)
        if amount is None:
            return None, None, "tarifa_native_incompleta_para_perfil"
        balance = _decimal(native.get("available_balance_usd"))
        availability = row.get("availability") or {}
        if availability.get("balance_confirmed") is not True:
            return None, None, "saldo_nao_confirmado"
        if balance is None or balance < 0:
            return None, None, "saldo_desconhecido"
        if balance < amount:
            return None, balance, "saldo_insuficiente"
        return amount, balance - amount, None
    if mode == "go_quota":
        if not _has_token_profile(tokens):
            return None, None, "perfil_tokens_go_nao_configurado"
        remaining = row.get("quota_window_remaining")
        debit = row.get("quota_window_debit")
        if row.get("use_balance_fallback"):
            return None, None, "fallback_go_para_saldo_zen_nao_autorizado"
        if not isinstance(remaining, dict) or debit is None:
            return None, None, "quota_go_nao_confirmada"
        debit_map = debit if isinstance(debit, dict) else {window: debit for window in WINDOWS}
        headrooms: list[Decimal] = []
        for window in WINDOWS:
            available = _decimal(remaining.get(window))
            used = _decimal(debit_map.get(window))
            if available is None or used is None or available < 0 or used < 0:
                return None, None, f"janela_go_{window}_desconhecida"
            if used > available:
                return None, None, f"quota_go_{window}_insuficiente"
            headrooms.append(available - used)
        representative = _decimal(debit_map.get("monthly"))
        if representative is None:
            return None, min(headrooms), "debito_go_nao_confirmado"
        return representative, min(headrooms), None
    if mode == "claude_subscription":
        amount = _decimal(row.get("subscription_consumption_usd"))
        if amount is None:
            return None, None, "consumo_assinatura_nao_mensuravel"
        return amount, None, None
    return None, None, "modo_de_cobranca_desconhecido"


def route(candidates: Iterable[dict[str, Any]], role: str, *, allowed_providers: Iterable[str] = (),
          tokens: dict[str, Any] | None = None, budget_usd: Any = None, allow_proxy: bool = False,
          delta_points: Any = None, max_price_age_hours: Any = 24, max_score_age_days: Any = 30,
          now: dt.datetime | None = None, band_override: str | None = None,
          bands: dict[str, Any] | None = None,
          benchmark_metric: str = "aa_coding_agent_index_v1.5") -> dict[str, Any]:
    """Returns the stable API: selected, ranking, reason. Never dispatches a model."""
    default_band = ROLE_BANDS.get(role)
    if default_band is None:
        return {"selected": None, "ranking": [], "reason": f"papel_desconhecido:{role}"}
    normalized_bands = validate_bands(bands)
    band = band_override or default_band
    if band not in normalized_bands:
        raise ValueError("band deve ser uma faixa fixa: leve, media ou alta")
    if benchmark_metric != "aa_coding_agent_index_v1.5":
        raise ValueError("benchmark_metric incompatível; somente aa_coding_agent_index_v1.5 é aceito")
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now precisa de timezone")
    now = now.astimezone(dt.timezone.utc)
    tokens = tokens or {}
    providers = set(allowed_providers)
    if not providers:
        return {"selected": None, "ranking": [], "reason": "provider_nao_autorizado; informe --providers explicitamente"}
    if budget_usd is None:
        budget = None
    else:
        budget = _decimal(budget_usd)
        if budget is None or budget < 0:
            raise ValueError("budget_usd precisa ser decimal não negativo")
    max_price_age = _decimal(max_price_age_hours)
    max_score_age = _decimal(max_score_age_days)
    if max_price_age is None or max_score_age is None:
        raise ValueError("TTL precisa ser decimal não negativo")
    delta = _decimal(delta_points) if delta_points is not None else DEFAULT_DELTA[band]
    if delta is None or delta < 0 or max_price_age < 0 or max_score_age < 0:
        raise ValueError("delta e TTL devem ser decimais não negativos")

    ranking = []
    eligible = []
    reasons_seen: list[str] = []
    for row in candidates:
        if not isinstance(row, dict):
            continue
        provider = row.get("provider")
        score = row.get("score") or {}
        parsed_score = _decimal(score.get("score"))
        row_band = _score_band(parsed_score, normalized_bands)
        reference = _profile_cost(row, tokens)
        native_cost, headroom, native_error = _native_cost_and_headroom(row, tokens)
        excluded: list[str] = []
        availability = row.get("availability") or {}
        if provider not in providers:
            excluded.append("provider_nao_autorizado")
        if availability.get("local_listed") is not True:
            excluded.append("nao_listado_localmente")
        if availability.get("authenticated") is not True:
            excluded.append("autenticacao_nao_confirmada")
        if availability.get("entitled") is not True:
            excluded.append("entitlement_nao_confirmado")
        required_provenance = all(score.get(field) not in (None, "", {}) for field in ("agent", "harness", "settings", "source_url", "observed_at"))
        if not required_provenance or not str(score.get("source_url", "")).startswith("https://artificialanalysis.ai/"):
            excluded.append("proveniencia_do_benchmark_incompleta")
        if score.get("variant") != row.get("variant"):
            excluded.append("mapeamento_de_variante_incompativel")
        expected_harness = EXPECTED_HARNESSES.get(row.get("tool"))
        if score.get("match_grade") == "exact" and score.get("harness") != expected_harness:
            excluded.append("harness_incompativel")
        if score.get("metric_id") != AA_METRIC or str(score.get("version")) != AA_VERSION:
            excluded.append("indice_incompativel_ou_ausente")
        if parsed_score is None:
            excluded.append("no_scored_candidate")
        if score.get("match_grade") not in (("exact", "proxy") if allow_proxy else ("exact",)):
            excluded.append("match_proxy_nao_autorizado" if score.get("match_grade") == "proxy" else "mapeamento_de_variante_incompativel")
        if row_band != band:
            excluded.append("fora_da_faixa" if row_band else "sem_faixa_de_nota")
        excluded.extend(_staleness(row, now, max_price_age, max_score_age, tokens))
        if native_error:
            excluded.append(native_error)
        if row.get("billing_mode") in ("zen_balance", "omp_payg") and budget is None:
            excluded.append("orcamento_zen_nao_configurado" if row.get("billing_mode") == "zen_balance" else "orcamento_payg_omp_nao_configurado")
        if native_cost is not None and budget is not None and native_cost > budget:
            excluded.append("orcamento_excedido")
        if row.get("billing_mode") == "claude_subscription" and native_cost is None:
            excluded.append("consumo_assinatura_nao_mensuravel")
        if row.get("billing_mode") == "go_quota" and headroom is None and native_error is None:
            excluded.append("cota_go_nao_confirmada")
        key = row.get("model_key") or f"{provider}/{row.get('model_id', '')}"
        entry = {
            "model_key": key, "provider": provider, "billing_mode": row.get("billing_mode"),
            "score": decimal_text(parsed_score), "band": row_band, "match_grade": score.get("match_grade"),
            "eligible": not excluded, "exclusion_reasons": excluded,
            "reference_cost_usd": decimal_text(reference), "native_cost_or_quota_debit_usd": decimal_text(native_cost),
            "quota_headroom_usd": decimal_text(headroom),
        }
        ranking.append(entry)
        if not excluded:
            eligible.append((row, entry, parsed_score, native_cost, headroom))
        else:
            reasons_seen.extend(excluded)
    ranking.sort(key=lambda entry: (
        not entry["eligible"],
        _decimal(entry.get("native_cost_or_quota_debit_usd")) if _decimal(entry.get("native_cost_or_quota_debit_usd")) is not None else Decimal("Infinity"),
        -(_decimal(entry.get("score")) or Decimal(0)),
        -(_decimal(entry.get("quota_headroom_usd")) or Decimal(0)),
        entry["model_key"],
    ))
    if not ranking:
        return {"selected": None, "ranking": [], "reason": "no_scored_candidate"}

    if not eligible:
        if "no_scored_candidate" in reasons_seen or "indice_incompativel_ou_ausente" in reasons_seen:
            reason = "no_scored_candidate_or_compatible_index"
        elif "fora_da_faixa" in reasons_seen or "sem_faixa_de_nota" in reasons_seen:
            reason = f"faixa_vazia:{band}"
        elif "quota_go_5h_insuficiente" in reasons_seen or "quota_go_weekly_insuficiente" in reasons_seen or "quota_go_monthly_insuficiente" in reasons_seen:
            reason = "quota_go_insuficiente; execução pausada antes da chamada"
        elif "fallback_go_para_saldo_zen_nao_autorizado" in reasons_seen:
            reason = "fallback_go_para_saldo_zen_nao_autorizado"
        else:
            reason = "nenhum_candidato_elegivel:" + ",".join(sorted(set(reasons_seen)))
        return {"selected": None, "ranking": ranking, "reason": reason}

    top_score = max(item[2] for item in eligible)
    plateau = [item for item in eligible if item[2] >= top_score - delta]
    # custo real da ferramenta; desempate: score, folga de quota, ID lexical.
    plateau.sort(key=lambda item: (item[3], -item[2], -(item[4] if item[4] is not None else Decimal(0)), item[1]["model_key"]))
    chosen = plateau[0]
    row, entry, score_value, native_cost, headroom = chosen
    selected = {
        "model_key": entry["model_key"],
        "billing_mode": {"zen_balance": "zen", "go_quota": "go", "omp_payg": "payg", "claude_subscription": "subscription"}.get(row.get("billing_mode"), row.get("billing_mode")),
        "billing_mode_detail": row.get("billing_mode"), "score": entry["score"],
        "band": band, "match_grade": entry["match_grade"],
        "reference_cost_usd": entry["reference_cost_usd"],
        "native_cost_or_quota_debit_usd": decimal_text(native_cost),
        "estimated_native_usd": decimal_text(native_cost) if row.get("billing_mode") in ("zen_balance", "omp_payg") else None,
        "native_tariff": row.get("native_tariff"),
        "available_balance_usd": (row.get("native_tariff") or {}).get("available_balance_usd"),
        "balance_confirmed": (row.get("availability") or {}).get("balance_confirmed") is True,
        "balance_verified_at": (row.get("availability") or {}).get("balance_verified_at"),
        "quota_window_remaining": row.get("quota_window_remaining"),
        "quota_window_debit": row.get("quota_window_debit"),
        "use_balance_fallback": row.get("use_balance_fallback") if row.get("billing_mode") == "go_quota" else False,
        "quota_headroom_usd": decimal_text(headroom),
        "score_top": decimal_text(top_score), "plateau_delta_points": decimal_text(delta),
    }
    if row.get("tool") == "omp":
        variant = row.get("variant")
        selected["dispatch_model_key"] = f"{row['provider']}/{row['model_id']}" + (f":{variant}" if variant else "")
    reason = f"menor consumo relevante dentro do platô {band} (score >= {decimal_text(top_score - delta)}); custo OpenRouter é apenas referência"
    if len(plateau) > 1:
        reason += "; desempate determinístico por consumo, score, folga de cota e model_key"
    return {"selected": selected, "ranking": ranking, "reason": reason}


def route_from_catalog(tool: str, role: str, allowed_providers: Iterable[str], cache_dir: str | Path | None = None,
                       *, explain: bool = False, tokens: dict[str, Any] | None = None, budget_usd: Any = None,
                       allow_proxy: bool = False, delta_points: Any = None, max_price_age_hours: Any = 24,
                       max_score_age_days: Any = 30, band_override: str | None = None,
                       bands: dict[str, Any] | None = None,
                       benchmark_metric: str = "aa_coding_agent_index_v1.5",
                       now: dt.datetime | None = None,
                       local_discoverer=discover_local_models, omp_discoverer=None) -> dict[str, Any]:
    from model_catalog import discover_omp_models
    clock = now or dt.datetime.now(dt.timezone.utc)
    snapshot = load_snapshot(tool, cache_dir)
    if snapshot is None:
        return {"selected": None, "ranking": [], "reason": "snapshot_de_catalogo_ausente; execute models sync"}
    if tool not in ("opencode", "omp"):
        return {"selected": None, "ranking": [], "reason": f"catalogo_local_nao_disponivel_para_{tool}"}
    providers = tuple(allowed_providers)
    if not providers:
        return route(snapshot.get("models", []), role, allowed_providers=providers, tokens=tokens, budget_usd=budget_usd,
                     allow_proxy=allow_proxy, delta_points=delta_points, max_price_age_hours=max_price_age_hours,
                     max_score_age_days=max_score_age_days, band_override=band_override, bands=bands,
                     benchmark_metric=benchmark_metric, now=clock)
    discoverer = local_discoverer if tool == "opencode" else (omp_discoverer or discover_omp_models)
    discoveries = {provider: discoverer(provider) for provider in sorted(set(providers))}
    verified_at = clock.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    candidates = []
    for original in snapshot.get("models", []):
        row = dict(original)
        availability = dict(row.get("availability") or {})
        provider = row.get("provider")
        result = discoveries.get(provider)
        if result is not None and result.get("ok"):
            local_ids = set(result.get("models", []))
            local_model_key = row["model_key"] if tool == "omp" else row["model_id"] + (f"#{row['variant']}" if row.get("variant") else "")
            availability["local_listed"] = local_model_key in local_ids
            availability["local_verified_at"] = result.get("verified_at", verified_at)
        elif provider in discoveries:
            availability["local_listed"] = None
            availability["local_verified_at"] = None
        row["availability"] = availability
        candidates.append(row)
    return route(candidates, role, allowed_providers=providers, tokens=tokens, budget_usd=budget_usd,
                 allow_proxy=allow_proxy, delta_points=delta_points, max_price_age_hours=max_price_age_hours,
                 max_score_age_days=max_score_age_days, band_override=band_override, bands=bands,
                 benchmark_metric=benchmark_metric, now=clock)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tool", choices=("opencode", "omp", "claude"), default="opencode")
    parser.add_argument("--role", required=True)
    parser.add_argument("--providers", default="")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("--cache-dir")
    args = parser.parse_args(argv)
    result = route_from_catalog(args.tool, args.role, [p for p in args.providers.split(",") if p], args.cache_dir, explain=True)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["selected"] is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
