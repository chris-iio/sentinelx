"""End-to-end pipeline integration tests.

Tests the full pipeline: extract -> normalize -> classify -> deduplicate.
Verifies that run_pipeline() returns correctly typed, deduplicated IOC objects.
"""

from pathlib import Path

from app.pipeline.extractor import _consume_extraction_source, run_pipeline
from app.pipeline.models import IOC, IOCType, append_ioc_by_type, group_by_type


class TestRunPipelineDeduplication:
    """Test that run_pipeline deduplicates identical normalized IOCs."""

    def test_duplicate_url_collapsed(self):
        """Same URL appearing twice in text -> one IOC result."""
        text = "Alert: hxxp://evil[.]com and hxxp://evil[.]com again"
        results = run_pipeline(text)
        url_results = [r for r in results if r.type == IOCType.URL]
        # Deduplicated: only 1 URL even though it appears twice
        assert len(url_results) == 1

    def test_mixed_defanged_with_duplicates(self):
        """Defanged URL appearing twice should be deduplicated; IP should appear once."""
        text = "Alert: hxxp://evil[.]com and hxxp://evil[.]com again, IP 192[.]168[.]1[.]1"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        # IPv4 must be present
        assert IOCType.IPV4 in types_found
        # evil.com URL should appear exactly once (deduplicated)
        evil_urls = [r for r in results if r.type == IOCType.URL and "evil.com" in r.value]
        assert len(evil_urls) == 1
        # IPv4 192.168.1.1 should appear exactly once (deduplicated)
        ipv4_results = [r for r in results if r.type == IOCType.IPV4]
        assert len(ipv4_results) == 1

    def test_duplicate_hash_collapsed(self):
        """Same hash appearing twice -> one IOC result."""
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        text = f"Hash {h} and also {h}"
        results = run_pipeline(text)
        hash_results = [r for r in results if r.type == IOCType.SHA256]
        assert len(hash_results) == 1

    def test_normalized_duplicate_variants_classified_once(self, monkeypatch):
        """Raw variants that normalize to one IOC should not repeat classification work."""
        classify_calls: list[tuple[str, str]] = []

        monkeypatch.setattr(
            "app.pipeline.extractor.extract_iocs",
            lambda _text: [
                {"raw": "hxxp://evil[.]com", "type_hint": "url"},
                {"raw": "http://evil.com", "type_hint": "url"},
            ],
        )

        def fake_classify(normalized_value: str, raw_match: str) -> IOC | None:
            classify_calls.append((normalized_value, raw_match))
            return IOC(type=IOCType.URL, value=normalized_value, raw_match=raw_match)

        monkeypatch.setattr("app.pipeline.extractor.classify", fake_classify)

        results = run_pipeline("unused")

        assert results == [
            IOC(type=IOCType.URL, value="http://evil.com", raw_match="hxxp://evil[.]com")
        ]
        assert classify_calls == [("http://evil.com", "hxxp://evil[.]com")]

    def test_type_value_duplicates_keep_first_output_order(self, monkeypatch):
        """Distinct normalized candidates that classify to one IOC keep the first result."""
        monkeypatch.setattr(
            "app.pipeline.extractor.extract_iocs",
            lambda _text: [
                {"raw": "first.example", "type_hint": "domain"},
                {"raw": "second.example", "type_hint": "domain"},
            ],
        )

        def fake_classify(normalized_value: str, raw_match: str) -> IOC | None:
            return IOC(type=IOCType.DOMAIN, value="shared.example", raw_match=raw_match)

        monkeypatch.setattr("app.pipeline.extractor.classify", fake_classify)

        results = run_pipeline("unused")

        assert results == [
            IOC(type=IOCType.DOMAIN, value="shared.example", raw_match="first.example")
        ]


class TestExtractionSourceConsumption:
    """Tests for shared extraction-source error handling."""

    def test_iocextract_sources_share_expected_error_policy(self):
        """iocextract extractors should route through one shared consumer helper."""
        added: list[tuple[str, str]] = []

        _consume_extraction_source(
            "test source",
            "url",
            lambda: [" http://evil.example "],
            lambda raw, type_hint: added.append((raw.strip(), type_hint)),
        )
        _consume_extraction_source(
            "bad source",
            "url",
            lambda: (_ for _ in ()).throw(ValueError("bad extractor")),
            lambda raw, type_hint: added.append((raw, type_hint)),
        )

        source = Path("app/pipeline/extractor.py").read_text(encoding="utf-8")
        assert added == [("http://evil.example", "url")]
        assert source.count("_consume_extraction_source(") == 5
        assert source.count("Unexpected error in %s extraction") == 1


class TestRunPipelineTypes:
    """Test that run_pipeline correctly classifies IOC types."""

    def test_single_candidate_skips_dedup_loop(self, monkeypatch):
        """One extracted candidate should classify directly without iterating for dedup."""

        class SingleCandidateList(list):
            def __iter__(self):
                raise AssertionError("single-candidate pipeline should not enter dedup loop")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("single-candidate pipeline should not slice candidates")
                return super().__getitem__(index)

        monkeypatch.setattr(
            "app.pipeline.extractor.extract_iocs",
            lambda _text: SingleCandidateList([{"raw": "8.8.8.8", "type_hint": "ipv4"}]),
        )

        results = run_pipeline("unused")

        assert results == [IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")]

    def test_pair_candidates_skip_dedup_loop(self, monkeypatch):
        """Two extracted candidates should classify directly without iterating for dedup."""

        class PairCandidateList(list):
            def __iter__(self):
                raise AssertionError("pair-candidate pipeline should not enter dedup loop")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("pair-candidate pipeline should not slice candidates")
                return super().__getitem__(index)

        monkeypatch.setattr(
            "app.pipeline.extractor.extract_iocs",
            lambda _text: PairCandidateList([
                {"raw": "8.8.8.8", "type_hint": "ipv4"},
                {"raw": "example.com", "type_hint": "domain"},
            ]),
        )

        results = run_pipeline("unused")

        assert results == [
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
            IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com"),
        ]

    def test_pair_candidate_path_preserves_dedup_semantics(self, monkeypatch):
        """The pair fast path should still keep first occurrence wins behavior."""

        monkeypatch.setattr(
            "app.pipeline.extractor.extract_iocs",
            lambda _text: [
                {"raw": "first.example", "type_hint": "domain"},
                {"raw": "second.example", "type_hint": "domain"},
            ],
        )

        def fake_classify(normalized_value: str, raw_match: str) -> IOC | None:
            return IOC(type=IOCType.DOMAIN, value="shared.example", raw_match=raw_match)

        monkeypatch.setattr("app.pipeline.extractor.classify", fake_classify)

        assert run_pipeline("unused") == [
            IOC(type=IOCType.DOMAIN, value="shared.example", raw_match="first.example")
        ]

    def test_ipv4_classified(self):
        text = "Suspicious IP 10.0.0.1 observed in traffic"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.IPV4 in types_found

    def test_url_classified(self):
        text = "Beacon to http://c2.malware.org/beacon detected"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.URL in types_found

    def test_sha256_classified(self):
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        text = f"File hash: {h}"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.SHA256 in types_found

    def test_cve_classified(self):
        text = "Exploits CVE-2025-49596 in the wild"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.CVE in types_found


class TestRunPipelineReturnType:
    """Test that run_pipeline returns correctly typed IOC objects."""

    def test_returns_list(self):
        results = run_pipeline("IP 192.168.1.1")
        assert isinstance(results, list)

    def test_returns_ioc_objects(self):
        results = run_pipeline("IP 192.168.1.1")
        for r in results:
            assert isinstance(r, IOC)

    def test_ioc_uses_slots_to_avoid_instance_dict(self):
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        assert not hasattr(ioc, "__dict__")

    def test_ioc_has_value(self):
        results = run_pipeline("IP 192.168.1.1")
        ipv4_results = [r for r in results if r.type == IOCType.IPV4]
        assert len(ipv4_results) >= 1
        assert ipv4_results[0].value == "192.168.1.1"

    def test_ioc_has_raw_match(self):
        """IOC.raw_match preserves the original string."""
        results = run_pipeline("IP 192.168.1.1")
        ipv4_results = [r for r in results if r.type == IOCType.IPV4]
        assert len(ipv4_results) >= 1
        assert ipv4_results[0].raw_match  # non-empty


class TestGroupByType:
    """Tests for template grouping helper."""

    def test_group_by_type_skips_iteration_for_empty_single_pair_or_three_ioc_lists(self):
        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short IOC grouping should not iterate")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("IOC grouping should not slice")
                return super().__getitem__(index)

        ioc = IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1")
        second_ipv4 = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        third_ipv4 = IOC(type=IOCType.IPV4, value="9.9.9.9", raw_match="9.9.9.9")
        domain = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com")

        assert group_by_type(NoIterList()) == {}
        assert group_by_type(NoIterList([ioc])) == {IOCType.IPV4: [ioc]}
        assert group_by_type(NoIterList([ioc, second_ipv4])) == {
            IOCType.IPV4: [ioc, second_ipv4]
        }
        assert group_by_type(NoIterList([ioc, domain])) == {
            IOCType.IPV4: [ioc],
            IOCType.DOMAIN: [domain],
        }
        assert group_by_type(NoIterList([ioc, second_ipv4, third_ipv4])) == {
            IOCType.IPV4: [ioc, second_ipv4, third_ipv4]
        }
        assert group_by_type(NoIterList([ioc, domain, second_ipv4])) == {
            IOCType.IPV4: [ioc, second_ipv4],
            IOCType.DOMAIN: [domain],
        }
        assert "len" in group_by_type.__code__.co_names

    def test_append_ioc_by_type_preserves_order_without_setdefault_empty_list_work(self):
        iocs = [
            IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
        ]
        grouped: dict[IOCType, list[IOC]] = {}

        append_ioc_by_type(grouped, iocs[0])
        append_ioc_by_type(grouped, iocs[1])

        assert grouped[IOCType.IPV4] == iocs
        assert append_ioc_by_type.__code__.co_names.count("setdefault") == 0

    def test_group_by_type_preserves_order_without_setdefault_empty_list_work(self):
        iocs = [
            IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
            IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com"),
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
        ]

        grouped = group_by_type(iocs)

        assert grouped[IOCType.IPV4] == [iocs[0], iocs[2]]
        assert grouped[IOCType.DOMAIN] == [iocs[1]]
        assert group_by_type.__code__.co_names.count("setdefault") == 0


class TestRunPipelineEdgeCases:
    """Edge cases for run_pipeline."""

    def test_empty_text_skips_extraction(self, monkeypatch):
        def fail_extract_iocs(_text):
            raise AssertionError("empty pipeline input should skip extraction")

        monkeypatch.setattr("app.pipeline.extractor.extract_iocs", fail_extract_iocs)

        assert run_pipeline("") == []

    def test_whitespace_only_text_skips_extraction(self, monkeypatch):
        class NoStripText(str):
            def strip(self, *args, **kwargs):
                raise AssertionError("whitespace-only pipeline input should not allocate strip output")

        def fail_extract_iocs(_text):
            raise AssertionError("whitespace-only pipeline input should skip extraction")

        monkeypatch.setattr("app.pipeline.extractor.extract_iocs", fail_extract_iocs)

        assert run_pipeline(NoStripText(" \t\n  ")) == []
        assert "has_non_whitespace" in run_pipeline.__code__.co_names

    def test_no_iocs_text(self):
        results = run_pipeline("Hello world, nothing suspicious here")
        assert results == []

    def test_realistic_threat_report(self):
        """Realistic threat report with IPv4, URL, hash, CVE."""
        text = (
            "The threat actor uses 198.51.100.42 as C2. "
            "Payload downloads from https://drop.evil.net/stage2. "
            "Sample hash: d41d8cd98f00b204e9800998ecf8427e. "
            "Exploits CVE-2024-12345."
        )
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        # At minimum: IP, URL, MD5, CVE
        assert IOCType.IPV4 in types_found
        assert IOCType.URL in types_found
        assert IOCType.MD5 in types_found
        assert IOCType.CVE in types_found
