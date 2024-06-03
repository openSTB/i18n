# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent


def test_support_singular_translation(inside_venv):
    from openstb.i18n.support import domain_translator, set_languages

    msg = "A simple test message"
    _ = domain_translator("openstb.i18n_test", plural=False)

    assert _(msg) == "A simple test message"
    set_languages("en")
    assert _(msg) == "A simple test message"
    set_languages("de")
    assert _(msg) == "Eine einfache Testmeldung"


def test_support_plural_translation(inside_venv):
    from openstb.i18n.support import domain_translator, set_languages

    msg = "{count:d} plugin was found"
    msgn = "{count:d} plugins were found"
    _n = domain_translator("openstb.i18n_test", plural=True)

    assert _n(msg, msgn, 1).format(count=1) == "1 plugin was found"
    assert _n(msg, msgn, 10).format(count=10) == "10 plugins were found"
    set_languages("de")
    assert _n(msg, msgn, 1).format(count=1) == "1 Plugin wurde gefunden"
    assert _n(msg, msgn, 10).format(count=10) == "10 Plugins wurden gefunden"
    set_languages("en")
    assert _n(msg, msgn, 1).format(count=1) == "1 plugin was found"
    assert _n(msg, msgn, 10).format(count=10) == "10 plugins were found"
