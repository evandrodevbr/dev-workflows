#!/usr/bin/env python3
"""Behavior tests for role routing, spending boundaries, and deterministic ties."""
import os
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import model_catalog
import model_router

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
NOW_TEXT = "2026-09-25T12:00:00Z"


def candidate(model_key, *, provider="opencode", score="45", native_input="0.0000001", billing="zen_balance", **extra):
    result = {
        "tool": "opencode", "model_key": model_key, "provider": provider,
        "model_id": model_key.split("/", 1)[-1], "variant": None, "billing_mode": billing,
        "availability": {"local_listed": True, "authenticated": True, "entitled": True, "verified_at": NOW_TEXT,
                         "local_verified_at": NOW_TEXT, "account_verified_at": NOW_TEXT,
                         "balance_confirmed": True, "balance_verified_at": NOW_TEXT},
        "score": {"metric_id": model_catalog.AA_METRIC, "version": "1.5", "score": score,
                  "agent": "Codex", "harness": "OpenCode", "variant": None, "settings": {"effort": "max"},
                  "match_grade": "exact", "source_url": model_catalog.AA_URL, "observed_at": NOW_TEXT},
        "openrouter": {"captured_at": NOW_TEXT, "price_per_token_usd": {"input": "0.0000001", "output": "0.0000005"}},
        "native_tariff": {"billing_mode": billing, "account_confirmed": True, "source_url": "https://opencode.ai/docs/zen",
                          "captured_at": NOW_TEXT, "available_balance_usd": "2",
                          "price_per_token_usd": {"input": native_input, "output": "0.0000002",
                                                   "cache_read": "0.00000001", "cache_write": "0.00000002"}},
    }
    if billing == "go_quota":
        result["quota_verified_at"] = NOW_TEXT
        result["quota_source_url"] = "https://opencode.ai/docs/go"
        result["use_balance_fallback"] = False
    result.update(extra)
    return result


class RoutePolicyTests(unittest.TestCase):
    def test_missing_cache_is_explicit_and_no_model_is_invented(self):
        with tempfile.TemporaryDirectory() as cache:
            result = model_router.route_from_catalog("opencode", "implementer", ["opencode"], cache)
        self.assertIsNone(result["selected"])
        self.assertIn("snapshot_de_catalogo_ausente", result["reason"])
        empty = model_router.route([], "explorer", allowed_providers=["opencode"], now=NOW)
        self.assertIsNone(empty["selected"])
        self.assertEqual(empty["reason"], "no_scored_candidate")
        high_only = model_router.route([candidate("opencode/high-only", score="54")], "implementer",
                                       allowed_providers=["opencode"], budget_usd="1", now=NOW)
        self.assertIsNone(high_only["selected"])
        self.assertEqual(high_only["reason"], "faixa_vazia:media")

    def test_benchmark_with_wrong_index_is_never_ranked(self):
        row = candidate("opencode/model-a", score="54")
        row["score"]["metric_id"] = "artificial_analysis_intelligence_index"
        result = model_router.route([row], "planner", allowed_providers=["opencode"], now=NOW)
        self.assertIsNone(result["selected"])
        self.assertEqual(result["ranking"][0]["eligible"], False)
        self.assertIn("indice_incompativel_ou_ausente", result["ranking"][0]["exclusion_reasons"])

    def test_role_band_precedes_cost_and_plateau_uses_native_cost_not_openrouter(self):
        cheap_high = candidate("opencode/high", score="54", native_input="0.000000001")
        media_best = candidate("opencode/media", score="49", native_input="0.0000001")
        media_cheaper = candidate("opencode/media-cheap", score="47", native_input="0.00000005")
        result = model_router.route([cheap_high, media_best, media_cheaper], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 1_000_000}, budget_usd="0.08", now=NOW)
        self.assertEqual(result["selected"]["model_key"], "opencode/media-cheap")
        self.assertEqual(result["selected"]["band"], "media")
        self.assertEqual(Decimal(result["selected"]["reference_cost_usd"]), Decimal("0.1"))
        self.assertEqual(Decimal(result["selected"]["estimated_native_usd"]), Decimal("0.05"))
        self.assertIn("platô", result["reason"])

    def test_zen_balance_must_cover_native_estimate_and_be_confirmed(self):
        row = candidate("opencode/model-a")
        row["native_tariff"]["available_balance_usd"] = "0.05"
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 1_000_000}, budget_usd="1", now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("saldo_insuficiente", result["ranking"][0]["exclusion_reasons"])
        row["native_tariff"]["available_balance_usd"] = "1"
        row["availability"]["balance_confirmed"] = False
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 1_000_000}, budget_usd="1", now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("saldo_nao_confirmado_ou_obsoleto", result["ranking"][0]["exclusion_reasons"])

    def test_zen_balance_requires_explicit_budget(self):
        row = candidate("opencode/model-a")
        result = model_router.route([row], "implementer", allowed_providers=["opencode"], now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("orcamento_zen_nao_configurado", result["ranking"][0]["exclusion_reasons"])

    def test_exact_benchmark_harness_must_match_tool_but_proxy_requires_approval(self):
        row = candidate("opencode/model-a")
        row["score"]["harness"] = "Codex"
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 100_000}, budget_usd="1", now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("harness_incompativel", result["ranking"][0]["exclusion_reasons"])

        row["score"]["match_grade"] = "proxy"
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 100_000}, budget_usd="1", now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("match_proxy_nao_autorizado", result["ranking"][0]["exclusion_reasons"])
        approved = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                      tokens={"input": 100_000}, budget_usd="1", allow_proxy=True, now=NOW)
        self.assertEqual(approved["selected"]["model_key"], "opencode/model-a")

    def test_budget_is_applied_before_plateau_and_proxy_requires_explicit_permission(self):
        top = candidate("opencode/top", score="49", native_input="0.000001")
        lower = candidate("opencode/lower", score="46", native_input="0.00000005")
        row = candidate("opencode/proxy", score="45", match="proxy")
        row["score"]["match_grade"] = "proxy"
        result = model_router.route([top, lower, row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 1_000_000}, budget_usd="0.1", now=NOW)
        self.assertEqual(result["selected"]["model_key"], "opencode/lower")
        exclusions = {entry["model_key"]: entry["exclusion_reasons"] for entry in result["ranking"]}
        self.assertIn("match_proxy_nao_autorizado", exclusions["opencode/proxy"])
        proxy = model_router.route([row], "implementer", allowed_providers=["opencode"], tokens={"input": 1_000_000},
                                   budget_usd="1", allow_proxy=True, now=NOW)
        self.assertEqual(proxy["selected"]["model_key"], "opencode/proxy")

    def test_unknown_entitlement_and_provider_are_not_eligible(self):
        row = candidate("opencode/model-a", score="54")
        row["availability"]["entitled"] = None
        result = model_router.route([row], "planner", allowed_providers=["opencode"], now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("entitlement_nao_confirmado", result["ranking"][0]["exclusion_reasons"])
        unauthorized = model_router.route([candidate("opencode/model-a", score="54")], "planner", now=NOW)
        self.assertIn("provider_nao_autorizado", unauthorized["reason"])

    def test_go_quota_checks_every_window_and_never_falls_back_to_zen(self):
        for window in model_router.WINDOWS:
            row = candidate("opencode-go/model-a", provider="opencode-go", score="54", billing="go_quota")
            row["quota_window_remaining"] = {"5h": "1", "weekly": "1", "monthly": "1"}
            row["quota_window_debit"] = {"5h": "0.1", "weekly": "0.1", "monthly": "0.1"}
            row["quota_window_remaining"][window] = "0.05"
            result = model_router.route([row], "planner", allowed_providers=["opencode-go"], tokens={"input": 1_000_000}, now=NOW)
            self.assertIsNone(result["selected"], window)
            self.assertIn("quota_go_insuficiente", result["reason"])
        row = candidate("opencode-go/model-a", provider="opencode-go", score="54", billing="go_quota")
        row["quota_window_remaining"] = {"5h": "1", "weekly": "1", "monthly": "1"}
        row["quota_window_debit"] = {"5h": "0.1", "weekly": "0.1", "monthly": "0.1"}
        row["use_balance_fallback"] = True
        result = model_router.route([row], "planner", allowed_providers=["opencode-go"], tokens={"input": 1_000_000}, now=NOW)
        self.assertIsNone(result["selected"])
        self.assertEqual(result["reason"], "fallback_go_para_saldo_zen_nao_autorizado")

    def test_go_success_exposes_quota_and_billing_mode_separately(self):
        row = candidate("opencode-go/model-a", provider="opencode-go", score="54", billing="go_quota")
        row["quota_window_remaining"] = {"5h": "1", "weekly": "2", "monthly": "3"}
        row["quota_window_debit"] = {"5h": "0.1", "weekly": "0.1", "monthly": "0.2"}
        result = model_router.route([row], "planner", allowed_providers=["opencode-go"], tokens={"input": 1_000_000}, now=NOW)
        selected = result["selected"]
        self.assertEqual(selected["billing_mode"], "go")
        self.assertEqual(selected["billing_mode_detail"], "go_quota")
        self.assertEqual(selected["quota_window_debit"]["monthly"], "0.2")
        self.assertIsNone(selected["estimated_native_usd"])
        self.assertEqual(selected["native_cost_or_quota_debit_usd"], "0.2")

    def test_missing_cache_rate_disables_comparative_cost_not_native_selection(self):
        row = candidate("opencode/model-a", score="45")
        row["openrouter"]["price_per_token_usd"] = {"input": "0.0000001"}
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    tokens={"input": 1_000_000, "cache_read": 1000}, budget_usd="1", now=NOW)
        self.assertEqual(result["selected"]["model_key"], "opencode/model-a")
        self.assertIsNone(result["selected"]["reference_cost_usd"])
        self.assertEqual(Decimal(result["selected"]["estimated_native_usd"]), Decimal("0.10001"))

    def test_expired_paid_metadata_blocks_automatic_selection(self):
        row = candidate("opencode/model-a", score="54")
        row["openrouter"]["captured_at"] = "2026-09-23T00:00:00Z"
        result = model_router.route([row], "planner", allowed_providers=["opencode"], budget_usd="1", now=NOW)
        self.assertIsNone(result["selected"])
        self.assertIn("preco_referencial_obsoleto_ou_ausente", result["ranking"][0]["exclusion_reasons"])

    def test_ties_are_deterministic_independent_of_input_order(self):
        a = candidate("opencode/a", score="48", native_input="0.00000005")
        b = candidate("opencode/b", score="48", native_input="0.00000005")
        first = model_router.route([a, b], "implementer", allowed_providers=["opencode"], tokens={"input": 1_000_000}, budget_usd="1", now=NOW)
        second = model_router.route([b, a], "implementer", allowed_providers=["opencode"], tokens={"input": 1_000_000}, budget_usd="1", now=NOW)
        self.assertEqual(first, second)
        self.assertEqual(first["selected"]["model_key"], "opencode/a")

    def test_fixed_bands_metric_and_role_override_contract(self):
        self.assertEqual(model_router.validate_bands({"leve": [10, 20], "media": [20, 50], "alta": [50, 100]}),
                         model_router.FIXED_BANDS)
        with self.assertRaises(ValueError):
            model_router.validate_bands({"leve": [0, 20], "media": [20, 50], "alta": [50, 100]})
        row = candidate("opencode/model-a", score="54")
        result = model_router.route([row], "implementer", allowed_providers=["opencode"],
                                    band_override="alta", tokens={"input": 1_000_000}, budget_usd="1", now=NOW)
        self.assertEqual(result["selected"]["band"], "alta")
        with self.assertRaises(ValueError):
            model_router.route([row], "planner", allowed_providers=["opencode"],
                               benchmark_metric="aa_coding_agent_index_v1.4", now=NOW)

    def test_omp_payg_uses_only_native_estimate_and_exact_dispatch_variant(self):
        row = candidate("openai/model-a#high", provider="openai", score="54", billing="omp_payg")
        row.update({"tool": "omp", "model_id": "model-a", "variant": "high"})
        row["score"]["harness"] = "OMP"
        row["score"]["variant"] = "high"
        row["openrouter"] = None
        row["native_tariff"] = {
            "billing_mode": "omp_payg", "account_confirmed": True,
            "source_url": "https://provider.example/pricing", "captured_at": NOW_TEXT,
            "price_per_token_usd": {"input": "0.000001"}, "available_balance_usd": "0.2",
        }
        result = model_router.route([row], "planner", allowed_providers=["openai"],
                                    tokens={"input": 100_000}, budget_usd="0.2", now=NOW)
        selected = result["selected"]
        self.assertEqual(selected["model_key"], "openai/model-a#high")
        self.assertEqual(selected["dispatch_model_key"], "openai/model-a:high")
        self.assertEqual(selected["billing_mode"], "payg")
        self.assertEqual(selected["estimated_native_usd"], "0.100000")
        self.assertEqual(selected["available_balance_usd"], "0.2")
        self.assertIsNone(selected["reference_cost_usd"])
        row["availability"]["balance_confirmed"] = False
        blocked = model_router.route([row], "planner", allowed_providers=["openai"],
                                     tokens={"input": 100_000}, budget_usd="0.2", now=NOW)
        self.assertIsNone(blocked["selected"])
        self.assertIn("saldo_nao_confirmado_ou_obsoleto", blocked["ranking"][0]["exclusion_reasons"])

    def test_omp_catalog_route_revalidates_local_list_and_keeps_manual_entitlement(self):
        row = candidate("openai/model-a#high", provider="openai", score="54", billing="omp_payg")
        row.update({"tool": "omp", "model_id": "model-a", "variant": "high"})
        row["score"]["harness"] = "OMP"
        row["score"]["variant"] = "high"
        row["native_tariff"] = {
            "billing_mode": "omp_payg", "account_confirmed": True,
            "source_url": "https://provider.example/pricing", "captured_at": NOW_TEXT,
            "price_per_token_usd": {"input": "0.000001"}, "available_balance_usd": "0.2",
        }
        with tempfile.TemporaryDirectory() as cache:
            with open(os.path.join(cache, "catalog-omp.json"), "w", encoding="utf-8") as stream:
                json.dump({"tool": "omp", "models": [row]}, stream)
            result = model_router.route_from_catalog(
                "omp", "planner", ["openai"], cache, tokens={"input": 100_000}, budget_usd="0.2",
                omp_discoverer=lambda provider: {"ok": True, "models": ["openai/model-a#high"], "verified_at": NOW_TEXT},
                now=NOW,
            )
            unsupported = model_router.route_from_catalog(
                "omp", "planner", ["openai"], cache, tokens={"input": 100_000}, budget_usd="0.2",
                omp_discoverer=lambda provider: {"ok": True, "models": ["openai/model-a"], "verified_at": NOW_TEXT},
                now=NOW,
            )
            self.assertIsNone(unsupported["selected"])
            self.assertIn("nao_listado_localmente", unsupported["ranking"][0]["exclusion_reasons"])
        self.assertEqual(result["selected"]["dispatch_model_key"], "openai/model-a:high")



if __name__ == "__main__":
    unittest.main(verbosity=1)
