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
    def test_optional_failure_and_empty_search_are_reported_separately(self):
        row = {"channel": "example", "title": "Live", "viewers": 0, "live_for": "", "url": "https://twitch.tv/example"}
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "streams.md"
            with (
                patch.object(sys, "argv", ["streams.py", "--out", str(report)]),
                patch.object(streams, "twitch", return_value=[row]),
                patch.object(streams, "youtube", return_value=[]),
                patch.object(streams, "kick", side_effect=RuntimeError("HTTP 403")),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()) as errors,
            ):
                streams.main()
            text = report.read_text()

        self.assertIn("| example | Live | 0 |", text)
        self.assertIn("## YouTube\n\nNo live streams found.", text)
        self.assertIn("## Kick\n\nOptional provider unavailable: HTTP 403", text)
        self.assertIn("Kick: Optional provider unavailable", errors.getvalue())
