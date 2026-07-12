"""Explicit consent boundary for intake provider egress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class ConsentRequiredError(RuntimeError):
    """Raised when intake would send document bytes without user consent."""


@dataclass(frozen=True)
class ConsentReceipt:
    """Auditable record of the provider and the consent decision."""

    provider: str
    granted: bool
    mode: str
    statement: str


def require_consent(
    provider: str,
    *,
    configured_mode: str | None = None,
    consent: bool | None = None,
    ask: Callable[[str], bool] | None = None,
) -> ConsentReceipt:
    """Require consent before a provider can receive document bytes.

    ``always`` is an explicit user configuration value, not an implicit default.
    A false or absent answer fails closed.  Local classification does not call
    this function because no document bytes leave the machine.
    """
    provider_name = str(provider or "unknown")
    statement = (
        f"Intake will send document content to provider '{provider_name}'. "
        "Do you consent?"
    )
    if configured_mode == "always":
        return ConsentReceipt(provider_name, True, "config", statement)
    granted = consent
    mode = "explicit"
    if granted is None and ask is not None:
        granted = bool(ask(statement))
        mode = "prompt"
    if not granted:
        raise ConsentRequiredError(
            f"consent required before intake can send document bytes to {provider_name}"
        )
    return ConsentReceipt(provider_name, True, mode, statement)
