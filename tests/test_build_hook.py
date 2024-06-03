# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent


def test_build_hook_catalog_compiled_installed(test_project_venv):
    """build-hook: check catalogs are compiled and installed"""
    venv_python, venv_sitepkgs = test_project_venv

    # Check the directories and files for the compiled catalog exist.
    locale = venv_sitepkgs / "openstb" / "locale"
    assert locale.is_dir(), "base locale directory missing"
    for spec in ["en", "de"]:
        mo = locale / spec / "LC_MESSAGES" / "openstb.i18n_test.mo"
        assert mo.is_file(), f"compiled catalog for {spec} missing"
