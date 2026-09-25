#!/usr/bin/env python3
"""Behavior tests for model catalog imports and reports (stdlib only)."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import model_catalog as catalog


class CatalogImportTests(unittest.TestCase):
    def test_openrouter_keeps_per_token_units_and_missing_cache_is_not_free(self):
        payload = {"data": [{"id": "z-ai/glm-5.3", "name": "GLM", "pricing": {
            "prompt": "0.0000014", "completion": "0.0000044", "input_cache_read": "0.00000026"
        }}]}
        prices = catalog.parse_openrouter(payload)["z-ai/glm-5.3"]
        self.assertEqual(prices["price_unit"], "USD/token")
        self.assertEqual(prices["price_per_token_usd"]["input"], "0.0000014")
        self.assertEqual(Decimal(prices["display_usd_per_1m"]["input"]), Decimal("1.4"))
        self.assertEqual(Decimal(prices["display_usd_per_1m"]["cache_read"]), Decimal("0.26"))
        self.assertIsNone(prices["display_usd_per_1m"]["cache_write"])
        self.assertIsNone(catalog.reference_cost(prices["price_per_token_usd"], {"cache_write": 1}))
        self.assertEqual(catalog.reference_cost(prices["price_per_token_usd"], {"input": 1_000_000, "output": 10_000}), Decimal("1.444"))

    def test_negative_public_tariff_keeps_valid_models_and_is_not_costed(self):
        payload = {"data": [
            {"id": "openrouter/auto-beta", "pricing": {"prompt": "-0.000001", "completion": "0.1"}},
            {"id": "openai/valid", "pricing": {"prompt": "0.000002", "completion": "0.000003"}},
        ]}
        parsed = catalog.parse_openrouter(payload)
        self.assertEqual(catalog.reference_cost(parsed["openai/valid"]["price_per_token_usd"],
                                               {"input": 1_000_000}), Decimal("2"))
        invalid = parsed["openrouter/auto-beta"]
        self.assertEqual(invalid["conditions"]["unsupported_negative_prices"]["input"], "-0.000001")
        self.assertIsNone(invalid["price_per_token_usd"]["input"])
        self.assertIsNone(catalog.reference_cost(invalid["price_per_token_usd"], {"input": 1}))
        with self.assertRaises(ValueError):
            catalog.parse_openrouter(payload, {"openai/valid": {"price_per_token_usd": {"input": "-1"},
                "source_url": "https://example.test/pricing", "captured_at": "2026-09-25T00:00:00Z"}})


    def test_openrouter_price_overrides_preserve_conditions_and_unit(self):
        payload = {"data": [{"id": "openai/gpt-6-luna", "pricing": {"prompt": "0.1", "completion": "0.5"}, "context_length": 272000}]}
        overrides = {"openai/gpt-6-luna": {
            "display_usd_per_1m": {"input": "2.25", "output": "7.5"},
            "context_length": 272000, "ttl": "1h", "endpoint": "https://example.test/v2",
            "source_url": "https://example.test/pricing", "captured_at": "2026-09-25T00:00:00Z"
        }}
        record = catalog.parse_openrouter(payload, overrides)["openai/gpt-6-luna"]
        self.assertEqual(record["price_per_token_usd"]["input"], "0.00000225")
        self.assertEqual(Decimal(record["display_usd_per_1m"]["output"]), Decimal("7.5"))
        self.assertEqual(record["conditions"]["context_length"], 272000)
        self.assertEqual(record["conditions"]["ttl"], "1h")
        self.assertEqual(record["conditions"]["endpoint"], "https://example.test/v2")
        with self.assertRaises(ValueError):
            catalog.parse_openrouter(payload, {"missing/model": {"display_usd_per_1m": {"input": "1"}}})

    def test_context_and_cache_ttl_overrides_choose_the_matching_price_tier(self):
        payload = {"data": [{"id": "openai/gpt-6-luna", "pricing": {
            "prompt": "0.0000001", "completion": "0.0000005",
            "input_cache_write": "0.0000009", "input_cache_write_1h": "0.0000005"
        }}]}
        tier = {"min_context_tokens": 272001, "price_per_token_usd": {"input": "0.0000002", "output": "0.0000008"},
                "source_url": "https://openrouter.ai/docs/pricing", "captured_at": "2026-09-25T00:00:00Z"}
        record = catalog.parse_openrouter(payload, {"openai/gpt-6-luna": {"context_tiers": [tier]}})["openai/gpt-6-luna"]
        below = catalog.openrouter_price_for_profile(record, {"context_length": 272000})
        above = catalog.openrouter_price_for_profile(record, {"context_length": 272001})
        self.assertEqual(below["price_per_token_usd"]["input"], "0.0000001")
        self.assertEqual(above["price_per_token_usd"]["input"], "0.0000002")
        self.assertEqual(above["applied_context_tier"], 272001)
        self.assertEqual(catalog.reference_cost(record["price_per_token_usd"], {"cache_write": 100, "cache_write_ttl": "1h"}), Decimal("0.00005"))

    def test_provider_catalog_preserves_exact_variants_without_guessing(self):
        rows = catalog.parse_provider_catalog({"data": [
            {"id": "model-x", "name": "X", "variants": ["high", "max"]},
            {"id": "model-y"}
        ]}, "opencode", catalog.ZEN_URL)
        self.assertEqual([r["model_key"] for r in rows], ["opencode/model-x#high", "opencode/model-x#max", "opencode/model-y"])
        self.assertTrue(all(r["availability"]["authenticated"] is None for r in rows))
        with self.assertRaises(ValueError):
            catalog.parse_provider_catalog({"data": [{"id": "bad/id"}]}, "opencode", catalog.ZEN_URL)

    def test_aa_import_requires_consent_provenance_and_one_consistent_v15_record(self):
        snapshot = {
            "metric_id": catalog.AA_METRIC, "version": "1.5", "ingestion": "manual_audited",
            "terms_accepted": True, "source_url": catalog.AA_URL, "attribution": "Artificial Analysis Coding Agent Index",
            "captured_at": "2026-09-25T00:00:00Z", "records": [{
                "provider": "opencode", "model_id": "gpt-6-luna", "variant": "max", "score": "41",
                "agent": "Codex", "harness": "Codex", "settings": {"effort": "max"},
                "match_grade": "proxy", "evidence_url": catalog.AA_URL
            }]
        }
        row = catalog.validate_aa_snapshot(snapshot)[0]
        self.assertEqual((row["metric_id"], row["version"], row["score"], row["match_grade"]), (catalog.AA_METRIC, "1.5", "41", "proxy"))
        wrong_index = dict(snapshot, metric_id="artificial_analysis_intelligence_index")
        with self.assertRaises(ValueError):
            catalog.validate_aa_snapshot(wrong_index)
        duplicate = dict(snapshot, records=snapshot["records"] * 2)
        with self.assertRaisesRegex(ValueError, "inconsistente"):
            catalog.validate_aa_snapshot(duplicate)
        no_consent = dict(snapshot, terms_accepted=False)
        with self.assertRaises(ValueError):
            catalog.validate_aa_snapshot(no_consent)

    def test_local_discovery_never_returns_diagnostics_or_credential_text(self):
        class Result:
            returncode = 0
            stdout = "opencode/model-a#high\nAPI_KEY=do-not-store\n"
            stderr = "secret=do-not-print"
        result = catalog.discover_local_models("opencode", runner=lambda *args, **kwargs: Result())
        self.assertEqual(result["models"], ["model-a#high"])
        self.assertNotIn("do-not-store", json.dumps(result))
        self.assertNotIn("do-not-print", json.dumps(result))

    def test_omp_json_is_local_listing_only_and_never_proves_entitlement(self):
        payload = {"models": [{"provider": "openai", "id": "gpt-6-luna", "thinking": ["high"]}]}
        rows = catalog.parse_omp_models(payload, "openai")
        self.assertEqual(rows[0]["model_key"], "openai/gpt-6-luna")
        self.assertIsNone(rows[0]["availability"]["authenticated"])
        self.assertIsNone(rows[0]["availability"]["entitled"])

        class Result:
            returncode = 0
            stdout = json.dumps(payload)
            stderr = "account-private-value"
        calls = []
        result = catalog.discover_omp_models("openai", runner=lambda args, **kwargs: (calls.append(args) or Result()))
        self.assertEqual(calls, [["omp", "models", "openai", "--json"]])
        self.assertEqual(result["models"], ["openai/gpt-6-luna", "openai/gpt-6-luna#high"])
        self.assertNotIn("account-private-value", json.dumps(result))

    def test_omp_keeps_slash_ids_and_only_lists_advertised_thinking(self):
        payload = {"models": [
            {"provider": "openai", "id": "anthropic/claude-x",
             "selector": "openai/anthropic/claude-x", "thinking": ["low", "high"]}
        ]}
        rows = catalog.parse_omp_models(payload, "openai")
        self.assertEqual([row["model_key"] for row in rows], ["openai/anthropic/claude-x"])

        self.assertEqual(rows[0]["model_id"], "anthropic/claude-x")
        class Result:
            returncode = 0
            stdout = json.dumps(payload)
            stderr = ""
        discovered = catalog.discover_omp_models("openai", runner=lambda *args, **kwargs: Result())
        self.assertEqual(discovered["models"], [
            "openai/anthropic/claude-x", "openai/anthropic/claude-x#high", "openai/anthropic/claude-x#low"
        ])
        with self.assertRaises(ValueError):
            catalog.parse_omp_models({"models": [{"provider": "openai", "id": "anthropic/claude-x",
                "selector": "openai/claude-x"}]}, "openai")

    def test_openrouter_public_long_context_override_affects_reference_cost(self):
        record = catalog.parse_openrouter({"data": [{"id": "anthropic/model-x", "pricing": {
            "prompt": "0.000001", "completion": "0.000002",
            "overrides": [{"min_prompt_tokens": 272000, "prompt": "0.000003", "completion": "0.000004"}]
        }}]})["anthropic/model-x"]
        selected = catalog.openrouter_price_for_profile(record, {"input": 272000})
        self.assertEqual(selected["price_per_token_usd"]["input"], "0.000003")
        self.assertEqual(catalog.reference_cost(selected["price_per_token_usd"],
                                                {"input": 272000, "output": 10}), Decimal("0.81604"))

    def test_omp_sync_requires_manual_account_and_balance_evidence(self):
        with tempfile.TemporaryDirectory() as cache:
            availability_path = os.path.join(cache, "availability.json")
            native_path = os.path.join(cache, "overrides.json")
            aa_path = os.path.join(cache, "aa.json")
            timestamp = catalog.utc_now()
            with open(availability_path, "w", encoding="utf-8") as stream:
                json.dump({
                    "tool": "omp", "ingestion": "manual_audited", "user_confirmed": True,
                    "captured_at": timestamp, "records": [{
                        "provider": "openai", "model_id": "gpt-6-luna", "variant": "high",
                        "local_listed": True, "authenticated": True, "entitled": True,
                        "verified_at": timestamp, "source": "manual audited OMP account",
                        "balance_confirmed": True, "balance_verified_at": timestamp,
                    }],
                }, stream)
            with open(native_path, "w", encoding="utf-8") as stream:
                json.dump({"native_tariffs": {"openai/gpt-6-luna#high": {
                    "billing_mode": "omp_payg", "account_confirmed": True,
                    "source_url": "https://provider.example/pricing", "captured_at": timestamp,
                    "price_per_token_usd": {"input": "0.000001"}, "available_balance_usd": "2",
                }}}, stream)
            with open(aa_path, "w", encoding="utf-8") as stream:
                json.dump({
                    "metric_id": catalog.AA_METRIC, "version": "1.5", "ingestion": "manual_audited",
                    "terms_accepted": True, "source_url": catalog.AA_URL,
                    "attribution": "Artificial Analysis Coding Agent Index", "captured_at": timestamp,
                    "records": [{
                        "provider": "openai", "model_id": "gpt-6-luna", "variant": "high", "score": "54",
                        "agent": "Codex", "harness": "OMP", "settings": {"effort": "high"},
                        "match_grade": "exact", "evidence_url": catalog.AA_URL,
                    }, {
                        "provider": "openai", "model_id": "gpt-6-luna", "variant": "xhigh", "score": "60",
                        "agent": "Codex", "harness": "OMP", "settings": {"effort": "xhigh"},
                        "match_grade": "exact", "evidence_url": catalog.AA_URL,
                    }],
                }, stream)
            rows = catalog.parse_omp_models({"models": [{"provider": "openai", "id": "gpt-6-luna",
                                                          "thinking": ["high"]}]}, "openai")
            discover = lambda provider: {"ok": True, "models": ["openai/gpt-6-luna", "openai/gpt-6-luna#high"], "rows": rows,
                                        "source_hash": "a" * 64, "verified_at": timestamp, "reason": None}
            fetched = []
            def fetcher(url):
                fetched.append(url)
                payload = {"data": []}
                return payload, url, catalog.sha256(catalog.canonical_json(payload))
            result = catalog.sync("omp", ["openai"], cache, fetcher, aa_snapshot=aa_path,
                                  availability_snapshot=availability_path, price_overrides=native_path,
                                  omp_discoverer=discover)
            snapshot = catalog.load_snapshot("omp", cache)
        by_key = {row["model_key"]: row for row in snapshot["models"]}
        self.assertNotIn("openai/gpt-6-luna#xhigh", by_key)
        self.assertEqual(result["model_count"], 2)
        self.assertEqual(fetched, [catalog.OPENROUTER_URL])
        model = by_key["openai/gpt-6-luna#high"]
        self.assertEqual(model["score"]["version"], "1.5")
        self.assertEqual(model["billing_mode"], "omp_payg")
        self.assertTrue(model["availability"]["local_listed"])
        self.assertTrue(model["availability"]["entitled"])
        self.assertTrue(model["availability"]["balance_confirmed"])
        self.assertEqual(model["native_tariff"]["available_balance_usd"], "2")
        with self.assertRaisesRegex(ValueError, "providers explicitamente"):
            catalog.sync("omp", cache_dir=cache, fetcher=lambda url: ({}, url, "x"))
        with self.assertRaises(ValueError):
            catalog.validate_native_tariff_overrides({"openai/model": {
                "billing_mode": "omp_payg", "account_confirmed": True,
                "source_url": "https://provider.example/pricing", "captured_at": "2026-09-25T12:00:00Z",
                "price_per_token_usd": {"input": "0.1"},
            }})

    def test_manual_availability_and_native_tariff_are_auditable_without_secrets(self):
        with tempfile.TemporaryDirectory() as cache:
            availability = os.path.join(cache, "availability.json")
            with open(availability, "w", encoding="utf-8") as stream:
                json.dump({
                    "tool": "opencode", "ingestion": "manual_audited", "user_confirmed": True,
                    "captured_at": "2026-09-25T00:00:00Z",
                    "records": [{"provider": "opencode", "model_id": "model-a", "variant": None,
                                 "local_listed": True, "authenticated": True, "entitled": True,
                                 "verified_at": "2026-09-25T00:00:00Z", "source": "manual confirmation token=NEVER_PERSIST"}]
                }, stream)
            def fetcher(url):
                body = {"data": [{"id": "model-a"}]} if url == catalog.ZEN_URL else {"data": []}
                return body, url, catalog.sha256(catalog.canonical_json(body))
            catalog.sync("opencode", ("opencode",), cache, fetcher,
                         lambda provider: {"ok": True, "models": ["model-a"], "reason": None},
                         availability_snapshot=availability)
            snapshot = catalog.load_snapshot(cache_dir=cache)
            model = snapshot["models"][0]
            self.assertEqual(model["availability"]["authenticated"], True)
            self.assertEqual(model["availability"]["entitled"], True)
            self.assertEqual(model["availability"]["source"], "manual_audited")
            self.assertNotIn("NEVER_PERSIST", json.dumps(snapshot))
            self.assertIn("availability", snapshot["source_hashes"])

        tariff = catalog.validate_native_tariff_overrides({"opencode/model-a": {
            "billing_mode": "zen_balance", "account_confirmed": True, "source_url": "https://opencode.ai/docs/zen",
            "captured_at": "2026-09-25T00:00:00Z", "price_per_token_usd": {"input": "0.000001", "output": "0.000002"},
            "available_balance_usd": "2",
        }})
        self.assertEqual(tariff["opencode/model-a"]["price_per_token_usd"]["input"], "0.000001")
        self.assertEqual(tariff["opencode/model-a"]["available_balance_usd"], "2")
        with self.assertRaisesRegex(ValueError, "saldo disponível"):
            catalog.validate_native_tariff_overrides({"opencode/model-a": {
                "billing_mode": "zen_balance", "account_confirmed": True, "source_url": "https://opencode.ai/docs/zen",
                "captured_at": "2026-09-25T00:00:00Z", "price_per_token_usd": {"input": "0.000001"},
            }})

    def test_unknown_openrouter_id_override_is_rejected(self):
        payload = {"data": [{"id": "known/id", "pricing": {}}]}
        with self.assertRaises(ValueError):
            catalog.parse_openrouter(payload, {"typo/id": {"context_length": 100}})


class CatalogSnapshotTests(unittest.TestCase):
    def test_missing_cache_and_complete_report_keep_unavailable_models(self):
        with tempfile.TemporaryDirectory() as cache:
            self.assertEqual(catalog.list_models(cache_dir=cache), [])
            self.assertEqual(catalog._csv_text([]).splitlines()[0].split(","), list(catalog.LIST_FIELDS))
            source_catalogs = {
                catalog.ZEN_URL: {"data": [{"id": "glm-5.3", "name": "GLM"}, {"id": "unknown-model", "name": "Unknown"}]},
                catalog.GO_URL: {"data": [{"id": "gpt-6-luna", "name": "Luna"}]},
                catalog.OPENROUTER_URL: {"data": [{"id": "z-ai/glm-5.3", "pricing": {"prompt": "0.0000014", "completion": "0.0000044"}},
                                                    {"id": "openai/gpt-6-luna", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}}]},
            }
            def fetcher(url):
                body = source_catalogs[url]
                return body, url, catalog.sha256(catalog.canonical_json(body))
            def local(provider):
                ids = ["glm-5.3"] if provider == "opencode" else []
                return {"ok": True, "models": ids, "reason": None}
            result = catalog.sync("opencode", ("opencode", "opencode-go"), cache, fetcher, local)
            rows = catalog.list_models(cache_dir=cache)
            self.assertEqual(result["model_count"], 3)
            self.assertEqual(len(rows), 3)
            by_key = {row["model_key"]: row for row in rows}
            self.assertEqual(by_key["opencode/glm-5.3"]["disponivel_na_conta"], "n/d")
            self.assertEqual(by_key["opencode/unknown-model"]["openrouter_id"], "n/d")
            self.assertEqual(by_key["opencode/unknown-model"]["preco_or_entrada_usd_1m"], "n/d")
            self.assertEqual(by_key["opencode-go/gpt-6-luna"]["coding_index_nota"], "n/d")
            self.assertFalse(by_key["opencode-go/gpt-6-luna"]["disponivel_na_conta"])
            self.assertEqual(len(catalog.list_models(cache_dir=cache, show_missing=False)), 1)
            self.assertEqual(Decimal(by_key["opencode/glm-5.3"]["preco_or_entrada_usd_1m"]), Decimal("1.4"))


    def test_archived_cli_csv_reproduces_frozen_bytes_at_capture_time(self):
        archived_snapshot = os.path.join(ROOT, "docs", "model-catalog-snapshot-2026-09-25", "catalog-opencode.json")
        archived_csv = os.path.join(ROOT, "docs", "model-catalog-zen-go-2026-09-25.csv")
        with tempfile.TemporaryDirectory() as cache:
            shutil.copyfile(archived_snapshot, os.path.join(cache, "catalog-opencode.json"))
            result = subprocess.run([
                sys.executable, os.path.join(ROOT, "scripts", "model_catalog.py"), "list",
                "--tool", "opencode", "--format", "csv", "--cache-dir", cache,
                "--as-of-utc", "2026-09-25T07:18:38Z",
            ], capture_output=True, check=True)
        with open(archived_csv, "rb") as stream:
            expected = stream.read()
        self.assertEqual(hashlib.sha256(expected).hexdigest(),
                         "80e2930877b20e5c47d4fd18f394c17a4683b257ca715496e91c63520d528230")
        self.assertEqual(result.stdout, expected)
        self.assertEqual(len(result.stdout.splitlines()) - 1, 122)

    def test_archived_openrouter_override_changes_long_context_cost(self):
        cache = os.path.join(ROOT, "docs", "model-catalog-snapshot-2026-09-25")
        record = catalog.load_snapshot(cache_dir=cache)["openrouter"]["openai/gpt-6-sol"]
        below = catalog.openrouter_price_for_profile(record, {"input": 271999})
        above = catalog.openrouter_price_for_profile(record, {"input": 300000})
        self.assertEqual(catalog.reference_cost(below["price_per_token_usd"], {"input": 271999}),
                         Decimal("0.543998"))
        self.assertEqual(above["applied_context_tier"], 272000)
        self.assertEqual(catalog.reference_cost(above["price_per_token_usd"], {"input": 300000}),
                         Decimal("1.2"))


    def test_go_report_shows_all_confirmed_quota_windows_and_fallback_policy(self):
        with tempfile.TemporaryDirectory() as cache:
            timestamp = catalog.utc_now()
            native_path = os.path.join(cache, "quota.json")
            with open(native_path, "w", encoding="utf-8") as stream:
                json.dump({"native_tariffs": {"opencode-go/model-a": {
                    "billing_mode": "go_quota", "account_confirmed": True,
                    "source_url": "https://opencode.ai/docs/go", "captured_at": timestamp,
                    "quota_window_remaining": {"5h": "2", "weekly": "5", "monthly": "10"},
                    "quota_window_debit": {"5h": "0.5", "weekly": "0.5", "monthly": "0.5"},
                    "use_balance_fallback": False,
                }}}, stream)
            def fetcher(url):
                body = {"data": [{"id": "model-a"}]} if url == catalog.GO_URL else {"data": []}
                return body, url, catalog.sha256(catalog.canonical_json(body))
            catalog.sync("opencode", ("opencode-go",), cache, fetcher,
                         lambda _: {"ok": True, "models": ["model-a"], "reason": None},
                         price_overrides=native_path)
            report = catalog.list_models(cache_dir=cache)[0]["preco_native_ou_cota"]
            self.assertEqual(report["quota_window_remaining"], {"5h": "2", "weekly": "5", "monthly": "10"})
            self.assertEqual(report["quota_window_debit"]["monthly"], "0.5")
            self.assertFalse(report["use_balance_fallback"])

    def test_score_bands_are_fixed_inclusive_only_at_high_upper_bound(self):
        cases = {"9.99": None, "10": "leve", "19.99": "leve", "20": "media", "49.99": "media", "50": "alta", "100": "alta", "100.01": None}
        for score, expected in cases.items():
            self.assertEqual(catalog.band_for_score(score), expected)


if __name__ == "__main__":
    unittest.main(verbosity=1)
