# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent


def test_support_singular_translation(inside_venv):
    from openstb.i18n.support import translations

    msg = "A simple test message"
    trans = translations.load("openstb.i18n_test")

    assert trans.gettext(msg) == "A simple test message"
    translations.set_locales("en")
    assert trans.gettext(msg) == "A simple test message"
    translations.set_locales("de")
    assert trans.gettext(msg) == "Eine einfache Testmeldung"


def test_support_plural_translation(inside_venv):
    from openstb.i18n.support import translations

    msg = "{count:d} plugin was found"
    msgn = "{count:d} plugins were found"
    _n = translations.load("openstb.i18n_test").ngettext

    assert _n(msg, msgn, 1).format(count=1) == "1 plugin was found"
    assert _n(msg, msgn, 10).format(count=10) == "10 plugins were found"
    translations.set_locales("de")
    assert _n(msg, msgn, 1).format(count=1) == "1 Plugin wurde gefunden"
    assert _n(msg, msgn, 10).format(count=10) == "10 Plugins wurden gefunden"
    translations.set_locales("en")
    assert _n(msg, msgn, 1).format(count=1) == "1 plugin was found"
    assert _n(msg, msgn, 10).format(count=10) == "10 plugins were found"
