from __future__ import annotations

"""Compatibility wrapper for the retired desktop workbench entry.

The user-facing desktop application now lives in ``rim_data_analysis.desktop_user_app``.
This module remains only to preserve historical imports and older entry references.
"""

from rim_data_analysis.desktop_user_app import RimDataAnalysisDesktopApp, main

__all__ = ["RimDataAnalysisDesktopApp", "main"]
