# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from scripts import public_symbols_checker


class FakeRepo:
    def __init__(self, commits):
        self.commits = commits
        self.requested_refs = []

    def commit(self, ref):
        self.requested_refs.append(ref)
        try:
            return self.commits[ref]
        except KeyError as exc:
            raise ValueError(ref) from exc


def test_get_comparison_commit_defaults_to_main(monkeypatch):
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    main_commit = object()
    repo = FakeRepo({"main": main_commit})

    assert public_symbols_checker._get_comparison_commit(repo) is main_commit
    assert repo.requested_refs == ["main"]


def test_get_comparison_commit_uses_origin_base_for_main_pull_request(
    monkeypatch,
):
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    origin_main_commit = object()
    repo = FakeRepo(
        {
            "origin/main": origin_main_commit,
            "main": object(),
        }
    )

    assert (
        public_symbols_checker._get_comparison_commit(repo)
        is origin_main_commit
    )
    assert repo.requested_refs == ["origin/main"]


def test_get_comparison_commit_uses_origin_base_for_release_pull_request(
    monkeypatch,
):
    base_ref = "release/v1.41.x"
    monkeypatch.setenv("GITHUB_BASE_REF", base_ref)
    origin_release_commit = object()
    repo = FakeRepo(
        {
            f"origin/{base_ref}": origin_release_commit,
            "main": object(),
        }
    )

    assert (
        public_symbols_checker._get_comparison_commit(repo)
        is origin_release_commit
    )
    assert repo.requested_refs == [f"origin/{base_ref}"]


def test_get_comparison_commit_falls_back_to_local_base(monkeypatch):
    base_ref = "release/v1.41.x"
    monkeypatch.setenv("GITHUB_BASE_REF", base_ref)
    local_release_commit = object()
    repo = FakeRepo(
        {
            base_ref: local_release_commit,
            "main": object(),
        }
    )

    assert (
        public_symbols_checker._get_comparison_commit(repo)
        is local_release_commit
    )
    assert repo.requested_refs == [f"origin/{base_ref}", base_ref]
