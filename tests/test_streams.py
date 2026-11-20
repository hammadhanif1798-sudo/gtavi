import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import streams
import twitch


class TwitchDiscoveryTests(unittest.TestCase):
    def test_gta_alias_uses_canonical_category_and_requested_limit(self):
        stream = {"broadcaster": {"login": "example"}, "viewersCount": 5}
        with patch.object(twitch, "gql", side_effect=[
            {"data": {"searchCategories": {"edges": [{"node": {"name": "Grand Theft Auto V"}}]}}},
            {"data": {"game": {"streams": {"edges": [{"node": stream}]}}}},
        ]) as gql:
            rows = twitch.top_streams("gta 6", 3)

        self.assertEqual(rows[0]["login"], "example")
        self.assertIn("searchCategories(query:", gql.call_args_list[0].args[0])
        self.assertEqual(gql.call_args_list[1].args[1], {"name": "Grand Theft Auto VI", "n": 3})

    def test_graphql_error_in_successful_http_response_is_reported(self):
        with patch("requests.post") as post:
            post.return_value.json.return_value = {"errors": [{"message": "schema error"}]}
            with self.assertRaisesRegex(RuntimeError, "schema error"):
                twitch.gql(twitch._Q_SEARCH)


class StreamReportTests(unittest.TestCase):
    def run_report(self, platform, **providers):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            report = Path(directory) / "streams.md"
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            errors = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            for name in ("twitch", "youtube", "kick"):
                outcome = providers.get(name, [])
                settings = {"side_effect": outcome} if isinstance(outcome, BaseException) else {"return_value": outcome}
                stack.enter_context(patch.object(streams, name, **settings))
            status = streams.main(["--platform", platform, "--out", str(report)])
            return status, report.read_text(), errors.getvalue()

    def test_explicit_provider_failure_returns_nonzero_and_writes_report(self):
        for provider in ("twitch", "youtube", "kick"):
            with self.subTest(provider=provider):
                status, report, errors = self.run_report(
                    provider, **{provider: RuntimeError("HTTP 403")}
                )
                self.assertEqual(status, 1)
                self.assertIn("Required provider failed: HTTP 403", report)
                self.assertIn("Required provider failed: HTTP 403", errors)
                self.assertEqual(report.count("## "), 1)

    def test_empty_success_returns_zero(self):
        status, report, errors = self.run_report("twitch")
        self.assertEqual(status, 0)
        self.assertIn("## Twitch\n\nNo live streams found.", report)
        self.assertEqual(errors, "")

    def test_optional_failure_does_not_change_exit_code(self):
        status, report, errors = self.run_report("all", kick=RuntimeError("HTTP 404"))
        self.assertEqual(status, 0)
        self.assertIn("## YouTube\n\nNo live streams found.", report)
        self.assertIn("## Kick\n\nOptional provider unavailable: HTTP 404", report)
        self.assertIn("Kick: Optional provider unavailable", errors)

    def test_all_platforms_preserves_results_and_labels_both_failure_types(self):
        row = {"channel": "example", "title": "Live", "viewers": 0, "live_for": "",
               "url": "https://twitch.tv/example"}
        status, report, errors = self.run_report(
            "all", twitch=[row], youtube=SystemExit("yt-dlp missing"), kick=RuntimeError("HTTP 404")
        )
        self.assertEqual(status, 1)
        self.assertIn("| example | Live | 0 |", report)
        self.assertIn("## YouTube\n\nRequired provider failed: yt-dlp missing", report)
        self.assertIn("## Kick\n\nOptional provider unavailable: HTTP 404", report)
        self.assertIn("YouTube: Required provider failed", errors)
        self.assertIn("Kick: Optional provider unavailable", errors)
