"""Shared view package setup."""

import customtkinter as ctk

from text_editing import install_text_editing


def _install_on_root(root):
    install_text_editing(root)


# The main application imports the views package before creating GlowvaApp.
# Wrap the CustomTkinter root/toplevel constructors once so every window in
# the ERP receives the same editing behavior without changing each view.
if not getattr(ctk.CTk, "_glowva_text_editing_patched", False):
    _original_ctk_init = ctk.CTk.__init__

    def _ctk_init(self, *args, **kwargs):
        _original_ctk_init(self, *args, **kwargs)
        _install_on_root(self)

    ctk.CTk.__init__ = _ctk_init
    ctk.CTk._glowva_text_editing_patched = True


if not getattr(ctk.CTkToplevel, "_glowva_text_editing_patched", False):
    _original_toplevel_init = ctk.CTkToplevel.__init__

    def _toplevel_init(self, *args, **kwargs):
        _original_toplevel_init(self, *args, **kwargs)
        _install_on_root(self)

    ctk.CTkToplevel.__init__ = _toplevel_init
    ctk.CTkToplevel._glowva_text_editing_patched = True
