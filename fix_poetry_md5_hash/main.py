import sys
import argparse
from collections import defaultdict
import tempfile
import hashlib

from poetry.factory import Factory
from poetry.utils.helpers import download_file


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", default=".", help="Project directory")
    parsed_args = parser.parse_args(argv)
    fix_poetry_md5_hash(parsed_args.project_dir)


def fix_poetry_md5_hash(project_dir):
    poetry = Factory().create_poetry(project_dir)
    locker = poetry.locker
    lock_data = locker.lock_data
    pool = poetry.pool

    packages_to_update = defaultdict(list)
    for package_name, metadata_files in (
        lock_data.get("metadata", {}).get("files", {}).items()
    ):
        for index, file_info in enumerate(metadata_files):
            filename = file_info.get("file")
            hash = file_info.get("hash", "")
            if not filename or not hash.startswith("md5:"):
                continue

            packages_to_update[package_name].append(
                {"file_info": file_info, "index": index}
            )

    link_urls = {}
    for lock_package_data in lock_data.get("package", []):
        package_name = lock_package_data["name"]
        if package_name not in packages_to_update:
            continue

        package_version = lock_package_data["version"]
        package = pool.package(package_name, package_version)
        repo_name = lock_package_data.get("source", {}).get("reference")
        if repo_name:
            repo = pool.repository(repo_name)
            info(f"Getting links for {package_name} {package_version}")
            link_urls.update(
                {
                    link.filename: link.url_without_fragment
                    for link in repo.find_links_for_package(package)
                }
            )

    changed = False
    indices_to_delete = defaultdict(list)
    for package_name, metadata_files in packages_to_update.items():
        for file_info in metadata_files:
            index = file_info["index"]
            filename = file_info["file_info"]["file"]
            info(f"{filename} has MD5 hash")
            if filename not in link_urls:
                info(f"No link found for {filename}, deleting from lock file")
                indices_to_delete[package_name].append(index)
                changed = True
                continue

            hash = file_info["file_info"]["hash"]
            with tempfile.NamedTemporaryFile() as f:
                download_file(link_urls[filename], f.name)
                contents = f.read()

            md5_hash = hashlib.md5(contents).hexdigest()
            if hash != f"md5:{md5_hash}":
                info(
                    f"WARNING: {filename} hash {hash} does not match actual hash {md5_hash}"
                )
                continue

            info(f"{filename} has been updated for SHA256 hash")
            sha256_hash = hashlib.sha256(contents).hexdigest()
            file_info["file_info"]["hash"] = f"sha256:{sha256_hash}"
            changed = True

    for package_name, indices in indices_to_delete.items():
        for index in sorted(indices, reverse=True):
            del locker.lock_data["metadata"]["files"][package_name][index]

    if changed:
        info(f"Updating {locker.lock.path}")
        locker._write_lock_data(locker.lock_data)


def info(msg):
    print(msg, file=sys.stderr, flush=True)


if __name__ == "__main__":
    sys.exit(main())
