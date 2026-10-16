import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import release


def record(tag, **overrides):
    return {"tag_name": tag, "draft": False, "prerelease": False,
            "author": {"login": "github-actions[bot]"}, "assets": [], **overrides}


class ReleaseTests(unittest.TestCase):
    def test_latest_uses_semver_across_pages_and_ignores_drafts_and_prereleases(self):
        pages = [[record("v0.9.0"), record("v9.0.0", draft=True)],
                 [record("v0.10.0"), record("v1.0.0-rc.1", prerelease=True), record("other")]]
        with patch.object(release, "gh", return_value=json.dumps(pages)):
            self.assertEqual(release.latest_stable("openxbond/dashboard"), "v0.10.0")

    def test_existing_mismatched_bytes_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "dashboard.zip").write_bytes(b"expected")
            existing = record("v0.3.0", assets=[{"name": "dashboard.zip", "id": 123}])
            with patch.object(release, "gh", return_value=json.dumps([[existing]])) as api, \
                    patch.object(release.subprocess, "check_output", return_value=b"different"):
                with self.assertRaises(ValueError):
                    release.publish("openxbond/dashboard", "v0.3.0", directory)
                self.assertEqual(api.call_count, 1)

    def test_existing_non_bot_author_is_rejected_without_mutation(self):
        existing = record("v0.3.0", author={"login": "unexpected-account"})
        with patch.object(release, "gh", return_value=json.dumps([[existing]])) as api:
            with self.assertRaises(ValueError):
                release.publish("openxbond/dashboard", "v0.3.0", ".")
            self.assertEqual(api.call_count, 1)

    def test_existing_matching_assets_are_not_uploaded_again(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "dashboard.zip").write_bytes(b"same")
            (directory / "SHA256SUMS").write_bytes(b"checksum")
            existing = record("v0.3.0", assets=[{"name": "dashboard.zip", "id": 1}, {"name": "SHA256SUMS", "id": 2}])
            def api(*args):
                if args[0] == "api" and "--paginate" in args:
                    return json.dumps([[existing]])
                if args[0] == "api":
                    return json.dumps(existing)
                return ""
            with patch.object(release, "gh", side_effect=api) as calls, \
                    patch.object(release.subprocess, "check_output", side_effect=[b"same", b"checksum"]):
                release.publish("openxbond/dashboard", "v0.3.0", directory)
            self.assertFalse(any(call.args[:2] == ("release", "upload") for call in calls.call_args_list))
            self.assertFalse(any(call.args[:2] == ("release", "create") for call in calls.call_args_list))


if __name__ == "__main__":
    unittest.main()
