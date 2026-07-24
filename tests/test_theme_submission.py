import hashlib
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from scripts import theme_submission as submission


def make_theme_zip(manifest=None, extra_entries=None):
    manifest = manifest or {
        "name": "Test Theme",
        "short": "TestTheme",
        "description": "A test theme",
        "version": "1.2.3",
        "author": "Test Author",
    }
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("komari-theme.json", json.dumps(manifest))
        archive.writestr("dist/index.html", "<!doctype html>")
        for name, value in extra_entries or []:
            archive.writestr(name, value)
    return output.getvalue()


def issue_field(label, value):
    return f"### {label}\n\n{value}\n\n"


def github_issue_body(repository="https://github.com/example/theme"):
    return "".join(
        [
            issue_field(submission.GITHUB_REPOSITORY_FIELD, repository),
            issue_field(submission.PREVIEW_FIELD, "https://cdn.example.com/preview.png"),
            issue_field(
                submission.GITHUB_CONFIRMATION_FIELD,
                "- [x] "
                + submission.PUBLIC_RELEASE_CONFIRMATION
                + " / The repository must be public.",
            ),
        ]
    )


def external_issue_body(**overrides):
    values = {
        submission.PROJECT_URL_FIELD: "https://themes.example.com/test",
        submission.DOWNLOAD_FIELD: "https://downloads.example.com/test.zip",
        submission.PREVIEW_FIELD: "https://cdn.example.com/preview.png",
        submission.NAME_FIELD: "Test Theme Listing",
        submission.SHORT_FIELD: "TestTheme",
        submission.VERSION_FIELD: "1.2.3",
        submission.DESCRIPTION_FIELD: "Catalog description",
        submission.AUTHOR_FIELD: "Catalog Author",
        submission.EXTERNAL_CONFIRMATION_FIELD: "\n".join(
            [
                "- [x] " + submission.NO_MALICIOUS_CODE_CONFIRMATION,
                "- [X] " + submission.MANUAL_UPDATE_CONFIRMATION,
            ]
        ),
    }
    values.update(overrides)
    return "".join(issue_field(label, value) for label, value in values.items())


class FakeClient:
    def __init__(self, github=None, downloads=None):
        self.github = github or {}
        self.downloads = downloads or {}

    def get_github_json(self, path):
        value = self.github[path]
        if isinstance(value, Exception):
            raise value
        return value

    def download(self, url):
        value = self.downloads[url]
        if isinstance(value, Exception):
            raise value
        return value


class IssueFormTests(unittest.TestCase):
    def test_parse_issue_form_handles_crlf_and_no_response(self):
        body = (
            issue_field(submission.NAME_FIELD, "Test Theme")
            + issue_field(submission.DESCRIPTION_FIELD, "_No response_")
        ).replace("\n", "\r\n")
        fields = submission.parse_issue_form(body)
        self.assertEqual(fields[submission.NAME_FIELD], "Test Theme")
        self.assertEqual(fields[submission.DESCRIPTION_FIELD], "")

    def test_required_confirmation_must_be_checked(self):
        fields = submission.parse_issue_form(
            github_issue_body().replace("- [x]", "- [ ]")
        )
        with self.assertRaisesRegex(submission.SubmissionError, "请勾选确认项"):
            submission.require_checked_confirmations(
                fields,
                submission.GITHUB_CONFIRMATION_FIELD,
                [submission.PUBLIC_RELEASE_CONFIRMATION],
            )

    def test_repository_parser_normalizes_git_suffix(self):
        self.assertEqual(
            submission.parse_github_repository("https://www.github.com/Owner/Theme.git/"),
            ("Owner", "Theme"),
        )

    def test_repository_parser_rejects_subpaths(self):
        with self.assertRaises(submission.SubmissionError):
            submission.parse_github_repository("https://github.com/owner/theme/releases")


class PackageTests(unittest.TestCase):
    def test_inspect_valid_package(self):
        manifest = submission.inspect_theme_package(make_theme_zip())
        self.assertEqual(manifest["short"], "TestTheme")
        self.assertEqual(manifest["version"], "1.2.3")

    def test_manifest_must_be_at_archive_root(self):
        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("theme/komari-theme.json", "{}")
        with self.assertRaisesRegex(submission.SubmissionError, "根目录"):
            submission.inspect_theme_package(output.getvalue())

    def test_unsafe_archive_path_is_rejected(self):
        package = make_theme_zip(extra_entries=[("../outside.txt", "bad")])
        with self.assertRaisesRegex(submission.SubmissionError, "不安全路径"):
            submission.inspect_theme_package(package)

    def test_default_short_is_rejected(self):
        package = make_theme_zip(
            {
                "name": "Default",
                "short": "default",
                "version": "1.0.0",
                "author": "Author",
            }
        )
        with self.assertRaisesRegex(submission.SubmissionError, "不能为 default"):
            submission.inspect_theme_package(package)


class SubmissionTests(unittest.TestCase):
    repo_path = "/repos/example/theme"
    release_path = "/repos/example/theme/releases/latest"

    def github_client(self, assets):
        return FakeClient(
            github={
                self.repo_path: {
                    "private": False,
                    "html_url": "https://github.com/example/theme",
                },
                self.release_path: {"tag_name": "v1.2.3", "assets": assets},
            },
            downloads={
                asset["browser_download_url"]: asset["data"] for asset in assets
            },
        )

    def test_github_submission_selects_only_valid_zip(self):
        good = make_theme_zip()
        assets = [
            {
                "name": "source.zip",
                "browser_download_url": "https://github.com/example/theme/releases/download/v1/source.zip",
                "data": b"not a zip",
            },
            {
                "name": "theme.zip",
                "browser_download_url": "https://github.com/example/theme/releases/download/v1/theme.zip",
                "data": good,
            },
        ]
        result = submission.process_github_submission(
            submission.parse_issue_form(github_issue_body()),
            self.github_client(assets),
        )
        self.assertEqual(result.theme["short"], "TestTheme")
        self.assertEqual(result.asset_name, "theme.zip")
        self.assertEqual(result.release_tag, "v1.2.3")
        self.assertEqual(result.theme["sha256"], hashlib.sha256(good).hexdigest())
        self.assertEqual(result.theme["url"], "https://github.com/example/theme")

    def test_github_submission_rejects_multiple_valid_zips(self):
        package = make_theme_zip()
        assets = [
            {
                "name": "one.zip",
                "browser_download_url": "https://github.com/example/theme/releases/download/v1/one.zip",
                "data": package,
            },
            {
                "name": "two.ZIP",
                "browser_download_url": "https://github.com/example/theme/releases/download/v1/two.ZIP",
                "data": package,
            },
        ]
        with self.assertRaisesRegex(submission.SubmissionError, "多个有效主题 ZIP"):
            submission.process_github_submission(
                submission.parse_issue_form(github_issue_body()),
                self.github_client(assets),
            )

    def test_private_github_repository_is_rejected(self):
        client = FakeClient(github={self.repo_path: {"private": True}})
        with self.assertRaisesRegex(submission.SubmissionError, "不是公开仓库"):
            submission.process_github_submission(
                submission.parse_issue_form(github_issue_body()), client
            )

    def test_external_submission_uses_form_metadata_and_package_hash(self):
        package = make_theme_zip()
        url = "https://downloads.example.com/test.zip"
        result = submission.process_external_submission(
            submission.parse_issue_form(external_issue_body()),
            FakeClient(downloads={url: package}),
        )
        self.assertEqual(result.theme["name"], "Test Theme Listing")
        self.assertEqual(result.theme["author"], "Catalog Author")
        self.assertEqual(result.theme["sha256"], hashlib.sha256(package).hexdigest())

    def test_external_manifest_version_must_match_form(self):
        package = make_theme_zip()
        url = "https://downloads.example.com/test.zip"
        fields = submission.parse_issue_form(
            external_issue_body(**{submission.VERSION_FIELD: "9.9.9"})
        )
        with self.assertRaisesRegex(submission.SubmissionError, "版本与"):
            submission.process_external_submission(
                fields, FakeClient(downloads={url: package})
            )

    def test_external_github_project_url_is_rejected(self):
        fields = submission.parse_issue_form(
            external_issue_body(
                **{submission.PROJECT_URL_FIELD: "https://github.com/example/theme"}
            )
        )
        with self.assertRaisesRegex(submission.SubmissionError, "请使用 GitHub 主题模板"):
            submission.process_external_submission(fields, FakeClient())


class CatalogAndOutputTests(unittest.TestCase):
    def theme(self, short="TestTheme"):
        return {
            "name": "Test Theme",
            "short": short,
            "description": "Description",
            "version": "1.0.0",
            "author": "Author",
            "url": f"https://example.com/{short}",
            "preview": "https://example.com/preview.png",
            "download": f"https://example.com/{short}.zip",
            "sha256": "a" * 64,
        }

    def test_catalog_sorts_and_rejects_case_insensitive_duplicate(self):
        catalog = {"schema": 1, "themes": [self.theme("Zulu")]}
        submission.add_theme_to_catalog(catalog, self.theme("alpha"))
        self.assertEqual([item["short"] for item in catalog["themes"]], ["alpha", "Zulu"])
        with self.assertRaisesRegex(submission.SubmissionError, "already exists"):
            submission.add_theme_to_catalog(catalog, self.theme("ALPHA"))

    def test_pr_body_links_issue_and_contains_lifecycle_marker(self):
        result = submission.SubmissionResult(
            "external", self.theme(), "theme.zip"
        )
        body = submission.render_pr_body(result, 42)
        self.assertIn("Closes #42", body)
        self.assertIn("<!-- theme-submission-issue: 42 -->", body)
        self.assertIn("SHA-256", body)

    def test_success_comment_has_stable_refresh_marker(self):
        result = submission.SubmissionResult(
            "external", self.theme(), "theme.zip"
        )
        self.assertIn(
            "<!-- theme-submission-validation -->",
            submission.render_success_comment(result),
        )

    def test_failure_comment_explains_reopen_flow(self):
        comment = submission.render_failure_comment("invalid package")
        self.assertIn("重新打开", comment)
        self.assertIn("不需要新建 Issue", comment)
        self.assertIn("reopen", comment)

    def test_retry_comment_keeps_issue_open(self):
        comment = submission.render_retry_comment("temporary error")
        self.assertIn("Issue 将保持开启", comment)
        self.assertIn("The issue remains open", comment)

    def test_rejected_cli_keeps_catalog_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event_path = root / "event.json"
            catalog_path = root / "v1.json"
            comment_path = root / "comment.md"
            pr_body_path = root / "pr.md"
            output_path = root / "output.txt"
            event_path.write_text(
                json.dumps({"issue": {"number": 7, "body": github_issue_body()}}),
                encoding="utf-8",
            )
            original = {"schema": 1, "themes": [self.theme("TestTheme")]}
            catalog_path.write_text(json.dumps(original), encoding="utf-8")
            package = make_theme_zip()
            assets = [
                {
                    "name": "theme.zip",
                    "browser_download_url": "https://github.com/example/theme/releases/download/v1/theme.zip",
                    "data": package,
                }
            ]
            fake = SubmissionTests().github_client(assets)
            with mock.patch.object(submission, "HTTPClient", return_value=fake):
                exit_code = submission.main(
                    [
                        "--event",
                        str(event_path),
                        "--catalog",
                        str(catalog_path),
                        "--comment",
                        str(comment_path),
                        "--pr-body",
                        str(pr_body_path),
                        "--github-output",
                        str(output_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(catalog_path.read_text()), original)
            self.assertIn("status=failure", output_path.read_text())
            self.assertIn("自动检查失败", comment_path.read_text(encoding="utf-8"))
            self.assertFalse(pr_body_path.exists())


if __name__ == "__main__":
    unittest.main()
