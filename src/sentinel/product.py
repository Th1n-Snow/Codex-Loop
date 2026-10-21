"""Product identity and release metadata kept in one replaceable place."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductMetadata:
    display_name: str
    tagline: str
    version: str
    github_owner: str
    github_repo: str
    executable_name: str
    icon_filename: str
    version_resource_filename: str
    installer_filename: str
    checksum_filename: str
    app_data_folder: str
    legacy_app_data_folder: str
    legacy_install_folder: str
    publisher: str
    app_id: str

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.github_owner}/{self.github_repo}"

    @property
    def releases_url(self) -> str:
        return f"{self.github_url}/releases/latest"

    @property
    def issues_url(self) -> str:
        return f"{self.github_url}/issues"

    @property
    def bug_report_url(self) -> str:
        return f"{self.issues_url}/new?template=bug_report.yml"

    @property
    def feature_request_url(self) -> str:
        return f"{self.issues_url}/new?template=feature_request.yml"

    @property
    def release_api_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.github_owner}/"
            f"{self.github_repo}/releases/latest"
        )

    def linux_bundle_name(self, version: str, architecture: str = "x86_64") -> str:
        """The extracted folder name inside a Linux release archive.

        `scripts/build-linux.sh` reads this, so the published asset name and the
        name the updater looks for cannot drift apart.
        """
        return f"{self.display_name}-{version}-linux-{architecture}"

    def linux_archive_name(self, version: str, architecture: str = "x86_64") -> str:
        return f"{self.linux_bundle_name(version, architecture)}.tar.gz"

    def linux_checksum_name(self, version: str, architecture: str = "x86_64") -> str:
        return f"{self.linux_archive_name(version, architecture)}.sha256"

    @property
    def dist_folder_name(self) -> str:
        """PyInstaller COLLECT directory, derived so packaging cannot drift."""
        return self.executable_name.removesuffix(".exe")

    @property
    def single_instance_name(self) -> str:
        identifier = self.app_id.strip("{}")
        return f"Local\\{self.display_name}-{identifier}"

    @property
    def app_id_guid(self) -> str:
        """The stable Inno identity as a normal registry-key GUID."""
        return "{" + self.app_id.strip("{}") + "}"

    def packaging_metadata(self) -> dict[str, str]:
        """Every name the Windows build script needs, derived values included.

        `dataclasses.asdict` silently omits properties. The build script reads
        this explicit mapping so derived packaging names cannot drift.
        """
        from dataclasses import asdict

        data = {key: str(value) for key, value in asdict(self).items()}
        data["dist_folder_name"] = self.dist_folder_name
        data["linux_bundle_name"] = self.linux_bundle_name(self.version)
        data["linux_archive_name"] = self.linux_archive_name(self.version)
        data["single_instance_name"] = self.single_instance_name
        data["app_id_guid"] = self.app_id_guid
        return data


# Public repository for this independently maintained fork.
PRODUCT = ProductMetadata(
    display_name="Codex Loop",
    tagline="Codex quota warm-up",
    version="1.1.0",
    github_owner="Th1n-Snow",
    github_repo="Codex-Loop",
    executable_name="CodexLoop.exe",
    icon_filename="codexloop.ico",
    version_resource_filename="version_info.txt",
    installer_filename="CodexLoop-Setup.exe",
    checksum_filename="CodexLoop-Setup.exe.sha256",
    app_data_folder="CodexLoop",
    # A fresh fork install must not adopt UsageLoop's enabled schedules/guards.
    # Existing CodexLoop state is retained under its canonical directory.
    legacy_app_data_folder="CodexLoop",
    legacy_install_folder="Window Sentinel",
    publisher="Codex Loop",
    app_id="{{D469A7B2-486B-4E19-9C69-2E9EB1188BE3}",
)
