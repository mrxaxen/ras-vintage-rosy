import json
import requests
import wget
import os
import sys

from bs4 import BeautifulSoup
from string import Template
from urllib.parse import quote, urlsplit, urlunsplit

from rosy.models import VSManagerConfig
from rosy.rest_models import RestMod, RestModEntry, RestModRelease
from rosy.html_models import HtmlModEntry, HtmlModRelease

def release_exceptions(mod_entry: RestModEntry):
    if mod_entry.name in mods_with_version_exceptions:
        return mod_entry.releases[0]
    return None

def get_release_for_version_rest(version: str, mod_entry: RestModEntry) -> RestModRelease | None:
    ver_major, ver_minor, ver_patch = [int(e) for e in version.split(".")]

    for release in mod_entry.releases:
        if (
            "rc" in release.tags[-1] or
            "pre" in release.tags[-1]
        ):
            print("Release candidates are not supported, skipping..")
            continue

        rel_ver_major, rel_ver_minor, rel_ver_patch = [int(e) for e in release.tags[-1].split(".")]
        if version in release.tags:
            return release
        if (
            ver_major == rel_ver_major and
            ver_minor == rel_ver_minor and
            ver_patch >= rel_ver_patch
        ):
            return release
    return release_exceptions(mod_entry)

def get_release_for_version_html(version: str, mod_entry: HtmlModEntry) -> HtmlModRelease | None:
    ver_major, ver_minor, ver_patch = [int(e) for e in version.split(".")]
    for release in mod_entry.releases:
        if (
            "rc" in release.compatible_version_low or
            "pre" in release.compatible_version_low or
            (release.compatible_version_high and "rc" in release.compatible_version_high) or
            (release.compatible_version_high and "pre" in release.compatible_version_high)
        ):
            print("Release candidates are not supported, skipping..")
            continue

        rel_ver_low_major, rel_ver_low_minor, rel_ver_low_patch = [int(e) for e in release.compatible_version_low.split(".")]

        if not release.compatible_version_high:
            condition = all([
                ver_major == rel_ver_low_major,
                ver_minor == rel_ver_low_minor,
                ver_patch == rel_ver_low_patch or ver_patch > rel_ver_low_patch
            ])
            print(f"Exact ver compatible: {condition}")
        else:
            rel_ver_high_major, rel_ver_high_minor, rel_ver_high_patch = [int(e) for e in release.compatible_version_high.split(".")]
            condition = all([
                rel_ver_low_major <= ver_major and ver_major <= rel_ver_high_major,
                rel_ver_low_minor <= ver_minor and ver_minor <= rel_ver_high_minor,
                #rel_ver_low_patch <= ver_patch and ver_patch <= rel_ver_high_patch,
                rel_ver_low_patch <= ver_patch,
            ])
            print(f"Interval ver compatible: {condition}")

        if condition:
            print(f"Release candidate found for {mod_entry.name}: {release.filename}")
            return release

    print(f"No release candidate found for {mod_entry.name}")
    return None

def read_config() -> VSManagerConfig:
    with open("config.json", "r") as f:
        contents = json.load(f)
        return VSManagerConfig.model_validate(contents)

def get_releases_html(version: str, mod_id: str) -> tuple[HtmlModEntry, HtmlModRelease | None]:
    url=mod_html_url.substitute({"modid": mod_id})
    print(f"Checking for releases @ {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text)
    table = soup.find("table", class_="stdtable release-table gv")
    mod_name = soup.find("h2").find_all("span")[1].getText().strip()
    release_rows = table.find_all("tr", attrs={"data-assetid": True})

    releases = []
    for row in release_rows:
        compatible_versions = row.find(class_="tag").getText()
        download_button = row.find("a", class_=["mod-dl"])
        if not download_button:
            # Skip entries that cannot be downloaded
            continue
        filename = download_button.getText()
        print(f"{filename}, client: {version}, compatible with: {compatible_versions}")
        download_link = download_button['href']

        if " - " in compatible_versions:
            comp_ver_low, comp_ver_high = compatible_versions.split(" - ")
        else:
            comp_ver_low = compatible_versions
            comp_ver_high = None

        releases.append(HtmlModRelease(
            mainfile=f"{mod_domain}{download_link}",
            filename=filename,
            compatible_version_low=comp_ver_low,
            compatible_version_high=comp_ver_high
        ))

    mod_entry = HtmlModEntry(
        name=mod_name,
        modid=mod_id,
        releases=releases
    )

    return mod_entry, get_release_for_version_html(version, mod_entry)

def get_releases_rest(version: str, mod_id: str) -> tuple[RestModEntry | None, RestModRelease | HtmlModRelease | None]:
    print(f"Getting release info for mod: {mod_id}")
    response = requests.get(url=mod_endpoint_url.substitute({"modid": mod_id}))
    mod = RestMod.model_validate_json(response.text,extra="ignore")
    mod_entry = mod.mod

    release = None
    if mod.statuscode == "200":
        assert mod.mod
        release = get_release_for_version_rest(version, mod.mod)

    if mod.statuscode != "200" or release is None:
        print(f"{mod_id} status_code: {mod.statuscode}, release candidtate not found.")
        print(f"Attempting HTML based retrival for {mod_id}")
        mod_entry, release = get_releases_html(version, mod_id)

    return mod_entry, release

mod_domain = "https://mods.vintagestory.at"
mod_endpoint_url= Template(f"{mod_domain}/api/mod/$modid")
mod_html_url = Template(f"{mod_domain}/$modid#tab-files")
mods_with_version_exceptions = [
    "Canoe Mod"
]
config = read_config()
mod_releases: list[tuple[HtmlModEntry|RestModEntry, HtmlModRelease | RestModRelease | None]] = []

def main():
    if "rc" in config.version or "pre" in config.version:
        print("Release candidate  and pre-release versions are not supported, exiting..")
        sys.exit(0)

    for id in config.mods:
        release = None
        print("#################################")
        if "show" in id:
            mod_entry, release = get_releases_html(config.version, id)
        else:
            mod_entry, release = get_releases_rest(config.version, id)

        mod_releases.append((mod_entry, release))

    if not os.path.isdir(config.download_folder):
        os.mkdir(config.download_folder)

    for _, release in mod_releases:
        if release:

            parts = urlsplit(release.mainfile)
            encoded_path = quote(parts.path)
            encoded_query = quote(parts.query)
            encoded_fragment = quote(parts.fragment)
            encoded_url = urlunsplit((parts.scheme, parts.netloc, parts.path, encoded_query, encoded_fragment))

            print(f"Downloading: {release.filename} from: {encoded_url}")
            wget.download(encoded_url, out=f"{config.download_folder}/{release.filename}")

    for mod_entry, release in mod_releases:
        if not release:
            #print(f"Mod: {mod_entry.name} download: {"FAILED" if not release else "SUCCESS"}")
            print(f"Mod: {mod_entry.name} download: FAILED")

if __name__ == "__main__":
    main()
