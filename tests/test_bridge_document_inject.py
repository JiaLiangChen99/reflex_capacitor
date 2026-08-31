"""Tests for browser bridge script injection (reflex run)."""

from __future__ import annotations

from reflex_capacitor.plugin import inject_bridge_scripts_into_document


def test_inject_bridge_scripts_into_document_idempotent():
    raw = 'jsx("html",{},jsx("head",{},jsx("meta",{charSet:"utf-8"},)),jsx("body",{},))'
    once = inject_bridge_scripts_into_document(raw)
    assert '/reflex-capacitor/bridge.js"' in once
    assert '/reflex-capacitor/image-editor.js"' in once
    twice = inject_bridge_scripts_into_document(once)
    assert twice.count("/reflex-capacitor/bridge.js") == 1


def test_inject_bridge_scripts_noop_without_head():
    raw = 'jsx("div",{},"x")'
    assert inject_bridge_scripts_into_document(raw) == raw
