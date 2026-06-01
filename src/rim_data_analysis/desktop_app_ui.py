from __future__ import annotations

"""Compatibility wrapper for the retired intermediate desktop UI module.

The maintained desktop implementation now lives in ``rim_data_analysis.desktop_user_app``.
Keep this shim so older imports continue to resolve without carrying duplicate UI logic.
"""

from rim_data_analysis.desktop_user_app import RimDataAnalysisDesktopApp, main

__all__ = ["RimDataAnalysisDesktopApp", "main"]
