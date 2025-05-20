# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent

import logging
import os
from pathlib import Path
import subprocess
from typing import Any
import warnings

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

log = logging.getLogger(__name__)
log_level = logging.getLevelName(os.getenv("HATCH_BUILD_SCRIPTS_LOG_LEVEL", "INFO"))
log.setLevel(log_level)


class I18NBuildHooks(BuildHookInterface):
    PLUGIN_NAME = "openstb-i18n"

    def initialize(self, version: str, build_data: dict[str, Any]):
        if self.target_name == "wheel":
            # We need the domain to be specified.
            domain = self.config.get("domain")
            if domain is None:
                raise ValueError(
                    f"The `{self.PLUGIN_NAME}` hook option `domain` must be specified"
                )
            mo_fn = f"{domain}.mo"

            # Find the directory which contains input catalogs.
            root = Path(self.root)
            translation_dir = root / self.config.get("translation-dir", "translations")
            if not translation_dir.exists():
                warnings.warn(
                    f"directory for translation catalogs '{translation_dir}' does not "
                    "exist",
                    RuntimeWarning,
                )
                return

            # Find and compile each available catalog.
            locale_dir = root / "src" / "openstb" / "locale"
            for fn in translation_dir.iterdir():
                if not fn.is_file():
                    continue
                if fn.suffix != ".po":
                    continue

                # Compile it.
                locale_code = fn.stem
                log.info("compiling %s message catalog", locale_code)
                outfn = locale_dir / locale_code / "LC_MESSAGES" / mo_fn
                outfn.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["msgfmt", "-o", outfn, fn], check=True)

                # Add it to the artifacts included in the wheel.
                build_data["artifacts"].append(str(outfn))


@hookimpl
def hatch_register_build_hook():
    return I18NBuildHooks
