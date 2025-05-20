# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent

import gettext as _gettext
from importlib import resources
from importlib.resources.abc import Traversable
import logging
import os
from typing import Iterable

_logger = logging.getLogger(__name__)


def find_catalogs(locales: Iterable[str], domain: str) -> list[Traversable | None]:
    """Find translation catalogs.

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
    for locale in locales:
        _logger.debug("find_catalogs: locale %s", locale)
        for spec in _gettext._expand_lang(locale):  # type: ignore[attr-defined]
            if spec == "C":
                _logger.debug("find_catalogs: locale specification C")
                catalogs.append(None)
                break

            # Try to find the base message directories for this localespec. This may
            # find multiple options (especially if installed in editable mode) due to
            # our use of namespace packages.
            _logger.debug("find_catalogs: locale specification %s", spec)
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
                _logger.debug("find_catalogs: found catalog %s", catalog)
                catalogs.append(catalog)

    return catalogs


class DomainTranslation:
    """Translations for a single domain."""

    def __init__(self, domain: str):
        """
        Parameters
        ----------
        domain
            The translation domain, typically the name of the package or program.

        """
        self.domain = domain
        self.translations = _gettext.NullTranslations()

    def set_locales(self, *locales: str):
        """Set the locales to load messages from.

        Parameters
        ----------
        locales
            The locale codes to use in order of priority. These may be simply the
            desired language code (``en``) or include a specific variant (``de_AT``)
            and/or encoding (``de_AT.UTF-8``). If no locale codes are given, then
            environment variables will be used to try to determine the current locale.

        """
        ll = list(locales)
        if "C" not in locales:
            ll.append("C")

        is_base = True
        for catalog_path in find_catalogs(ll, self.domain):
            # Load the catalog.
            if catalog_path is None:
                _logger.debug("%s.set_locales: C", self.domain)
                translation = _gettext.NullTranslations()
            else:
                _logger.debug("%s.set_locales: %s", self.domain, catalog_path)
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
        message
            The unlocalised message.

        Returns
        -------
        str
            The localised version of ``message`` based on the current locale.

        """
        return self.translations.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Load the translation of a message considering plural forms.

        Note that the unlocalised message has a single plural form. Some languages have
        multiple plural forms.

        Parameters
        ----------
        singular, plural
            The singular and plural forms of the unlocalised message.
        n : int
            The number used to determine the form of the returned message.

        Returns
        -------
        str
            The localised version of the message based on the current locale.

        """
        return self.translations.ngettext(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str:
        """Load the context-dependent translation of a message.

        Parameters
        ----------
        context
            The message context.
        message
            The unlocalised message.

        Returns
        -------
        str
            The localised version of ``message`` based on the current locale.

        """
        return self.translations.pgettext(context, message)

    def npgettext(self, context: str, singular: str, plural: str, n: int) -> str:
        """Load the context-dependent translation of a message considering plural forms.

        Note that the unlocalised message has a single plural form. Some languages have
        multiple plural forms.

        Parameters
        ----------
        context
            The message context.
        singular, plural
            The singular and plural forms of the unlocalised message.
        n
            The number used to determine the form of the returned message.

        Returns
        -------
        str
            The localised version of the message based on the current locale.

        """
        return self.translations.npgettext(context, singular, plural, n)


class translations:
    """Translation manager."""

    _translations: dict[str, DomainTranslation] = {}
    _locales: list[str] = ["C"]

    @classmethod
    def load(cls, domain: str) -> DomainTranslation:
        """Load the translations for a particular domain.

        Parameters
        ----------
        domain
            The domain to get translations for. This is typically the name of the
            package or project.

        Returns
        -------
        DomainTranslation
            Interface to the translations. This will be set to the locales last given to
            `set_locales`.

        """
        if domain not in cls._translations:
            cls._translations[domain] = DomainTranslation(domain)
            cls._translations[domain].set_locales(*cls._locales)

        return cls._translations[domain]

    @classmethod
    def set_locales(cls, *locales: str):
        """Set the locale to use for all managed translations.

        Parameters
        ----------
        *locales
            The locale codes to use in order of priority. These may be simply the
            desired language code (``en``) or include a specific variant (``de_AT``)
            and/or encoding (``de_AT.UTF-8``). If no locale codes are given, then
            environment variables will be used to try to determine the current locale.

        """
        ll = list(locales)

        if not ll:
            for envname in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
                envval = os.environ.get(envname)
                if envval is not None:
                    _logger.debug(
                        "translation.set_locales: using env %s=%s", envname, envval
                    )
                    ll = envval.split(":")

        cls._locales = ll
        for translation in cls._translations.values():
            translation.set_locales(*cls._locales)
