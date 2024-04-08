# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent

import gettext as _gettext
from importlib import resources
from importlib.resources.abc import Traversable
import logging
import os
from typing import Callable, Iterable


_logger = logging.getLogger(__name__)


def _find_catalogs(languages: Iterable[str], domain: str) -> list[Traversable | None]:
    """Internal: find catalogs in the package resources.

    This will use `gettext._expand_lang` on each value in ``languages`` to get
    acceptable alternatives; for example, "en_NZ.UTF-8" would expand to ["en_NZ.UTF-8",
    "en_NZ", "en.UTF-8", "en"]. The `importlib.resources` module is then used to search
    for catalogs for each of these locales.

    If the "C" locale (meaning no localisation) is encountered, searching stops and a
    value of None is added to the list of catalogs.

    Parameters
    ----------
    languages : iterable
        An iterable of strings containing the language codes (and maybe country codes
        and/or encodings) for the desired languages.
    domain : str
        The translation domain to find catalogs for.

    Returns
    -------
    catalog_paths : list
        A list of `importlib.resources.abc.Traversable` instances representing the
        catalogs to be loaded. If the "C" locale was encountered in ``languages``,
        ``None`` is appended to the list and searching stops.

    """
    mo_fn = f"{domain}.mo"

    catalogs: list[Traversable | None] = []
    for language in languages:
        _logger.debug("_find_catalogs: language %s", language)
        for spec in _gettext._expand_lang(language):  # type: ignore[attr-defined]
            if spec == "C":
                _logger.debug("_find_catalogs: C locale requested, stop searching")
                catalogs.append(None)
                break

            # Try to find the base message directories for this localespec. This may
            # find multiple options (especially if installed in editable mode) due to
            # our use of namespace packages.
            _logger.debug("_find_catalogs: locale specification %s", spec)
            try:
                lc_messages = resources.files(f"openstb.locale.{spec}.LC_MESSAGES")
            except ModuleNotFoundError:
                continue

            # See if we have a catalog for this domain. joinpath() will search through
            # all multiplexed paths in lc_messages for mo_fn and return the first
            # existing file it finds. If it finds no existing files, it returns the
            # first path from lc_messages with mo_fn appended, hence we need the
            # is_file() check.
            catalog = lc_messages.joinpath(mo_fn)
            if catalog.is_file():
                _logger.debug("_find_catalogs: found catalog %s", catalog)
                catalogs.append(catalog)

    return catalogs


# The languages currently in use.
_languages: list[str] = ["C"]


class _DomainTranslations:
    """Internal: helper to manage translations for a domain."""

    def __init__(self, domain: str):
        self.domain = domain
        self.set_languages()

    def set_languages(self):
        """Update the catalogs in use for this domain."""
        is_base = True
        for catalog_path in _find_catalogs(_languages, self.domain):
            # Load the catalog.
            if catalog_path is None:
                _logger.debug("%s.set_languages: C", self.domain)
                translation = _gettext.NullTranslations()
            else:
                localespec = catalog_path.parent.parent.name
                _logger.debug("%s.set_languages: %s", self.domain, localespec)
                with catalog_path.open("rb") as catalog:
                    translation = _gettext.GNUTranslations(catalog)

            # add_fallback() will pass the new catalog to the end of the fallback chain.
            if is_base:
                self.translations = translation
                is_base = False
            else:
                self.translations.add_fallback(translation)

    def gettext(self, message: str) -> str:
        """Load the translation of a message.

        Parameters
        ----------
        message : str
            The unlocalised message.

        Returns
        -------
        str
            The localised version of ``message`` based on the current language and
            locale settings.

        """
        return self.translations.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Load the translation of a message considering plural forms.

        Note that the unlocalised message has a single plural form. Some languages have
        multiple plural forms.

        Parameters
        ----------
        singular, plural : str
            The singular and plural forms of the unlocalised message.
        n : int
            The number used to determine the form of the returned message.

        Returns
        -------
        str
            The localised version of the message based on the current language and
            locale settings.

        """
        return self.translations.ngettext(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str:
        """Load the context-dependent translation of a message.

        Parameters
        ----------
        context : str
            The message context.
        message : str
            The unlocalised message.

        Returns
        -------
        str
            The localised version of ``message`` based on the current language and
            locale settings.

        """
        return self.translations.pgettext(context, message)

    def npgettext(self, context: str, singular: str, plural: str, n: int) -> str:
        """Load the context-dependent translation of a message considering plural forms.

        Note that the unlocalised message has a single plural form. Some languages have
        multiple plural forms.

        Parameters
        ----------
        context : str
            The message context.
        singular, plural : str
            The singular and plural forms of the unlocalised message.
        n : int
            The number used to determine the form of the returned message.

        Returns
        -------
        str
            The localised version of the message based on the current language and
            locale settings.

        """
        return self.translations.npgettext(context, singular, plural, n)


# Track the domains we have loaded so we can update them.
_domain_translations: dict[str, "_DomainTranslations"] = {}


def set_languages(*languages: str):
    """Set the desired languages.

    Parameters
    ----------
    *languages
        Strings giving the language code for the desired language, optionally with a
        country code for a specific variant or an encoding specifier, e.g., "en", "de",
        "de_AT", "de_AT.UTF-8". These are used in the specified order: if a message is
        not translated by the catalogs for the first language, it will fall back to the
        catalogs for the second language and so on. If no languages are specified, then
        attempt to determine the current language of the user and use that if available.

    """
    global _languages

    if languages:
        _languages = list(languages)

    else:
        # Try to find settings in common environment variables.
        _languages.clear()
        for envname in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
            if envval := os.environ.get(envname):
                _logger.debug("set_languages: using env %s=%s", envname, envval)
                _languages = envval.split(":")
                break

    # Always include the no-localisation C locale as a fallback.
    if "C" not in _languages:
        _languages.append("C")

    # Update any existing domain instances.
    for translation in _domain_translations.values():
        translation.set_languages()


def domain_translator(domain: str, plural: bool, context: bool = False) -> Callable:
    """Get a domain-specific translator function.

    There are four possible translators which use the following call signatures based on
    the boolean parameters:

    plural, context:         f(context, singular, plural, n)
    not plural, context:     f(context, message)
    plural, not context:     f(singular, plural, n)
    not plural, not context: f(message)

    These correspond to the functions `npgettext`, `pgettext`, `ngettext` and `gettext`
    in the standard `gettext` library, respectively.

    Parameters
    ----------
    domain : str
        The domain to translate.
    plural : bool
        If True, get a translator which can handle plural forms. Otherwise, get a
        translator which handles single messages.
    context : bool
        If True, get a context-dependent translator. If False, get a translator without
        context support.

    Returns
    -------
    translator : callable

    """
    if domain not in _domain_translations:
        _domain_translations[domain] = _DomainTranslations(domain)

    if context:
        if plural:
            return _domain_translations[domain].npgettext
        return _domain_translations[domain].pgettext

    if plural:
        return _domain_translations[domain].ngettext
    return _domain_translations[domain].gettext
