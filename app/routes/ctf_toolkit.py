"""CTF toolkit routes: offline crypto/forensics helpers."""

from flask import current_app, flash, redirect, render_template, request, url_for

from app import limiter
from app.ctf import toolkit

from . import bp


def _render(result: dict | None = None, status: int = 200):
    return (
        render_template(
            "ctf_toolkit.html",
            tools=toolkit.TOOLS,
            result=result,
        ),
        status,
    )


@bp.route("/ctf/toolkit")
@limiter.limit("30 per minute")
def ctf_toolkit():
    """Offline crypto/forensics helper page."""
    return render_template("ctf_toolkit.html", tools=toolkit.TOOLS, result=None)


@bp.route("/ctf/toolkit/run", methods=["POST"])
@limiter.limit("30 per minute")
def ctf_toolkit_run():
    """Run one toolkit helper against text or an uploaded file."""
    tool = (request.form.get("tool") or "").strip()
    text = (request.form.get("input") or "")[: toolkit.MAX_INPUT_CHARS]

    if tool == "file-inspect":
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            flash("Choose a file to inspect.", "error")
            return redirect(url_for("main.ctf_toolkit"))
        data = upload.stream.read(toolkit.MAX_FILE_BYTES + 1)
        if len(data) > toolkit.MAX_FILE_BYTES:
            flash("File exceeds the 4 MB inspection limit.", "error")
            return redirect(url_for("main.ctf_toolkit"))
        return _render(
            {
                "tool": tool,
                "title": f"File inspection — {upload.filename}",
                "file": toolkit.identify_file(data),
                "strings": toolkit.extract_strings(data),
            }
        )

    if tool not in toolkit.TOOLS:
        flash("Unknown toolkit action.", "error")
        return redirect(url_for("main.ctf_toolkit"))
    key = (request.form.get("key") or "").strip()
    needs_text = tool not in ("cyclic", "cyclic-offset", "pack")
    if needs_text and not text.strip():
        flash("Input text is required.", "error")
        return redirect(url_for("main.ctf_toolkit"))
    if not needs_text and not (text.strip() or key):
        flash("Provide a value in the input or key/arg field.", "error")
        return redirect(url_for("main.ctf_toolkit"))

    try:
        result = _run_text_tool(tool, text)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.ctf_toolkit"))
    result["tool"] = tool
    return _render(result)


def _run_text_tool(tool: str, text: str) -> dict:
    if tool == "auto-decode":
        return {"title": "Auto-decode", "decodes": toolkit.auto_decode(text)}
    if tool in ("base64", "base32", "hex", "url", "rot13"):
        try:
            output = toolkit.decode_text(text, tool)
        except Exception:
            raise ValueError(f"Input is not valid {tool}.") from None
        return {"title": f"{tool} decode", "output": output}
    if tool == "caesar-brute":
        return {"title": "Caesar brute force", "rows": toolkit.caesar_brute(text)}
    if tool == "xor-brute":
        return {"title": "Single-byte XOR brute force", "rows": toolkit.xor_brute(text)}
    if tool == "hash-identify":
        return {"title": "Hash identification", "hash": toolkit.identify_hash(text)}
    if tool == "hash-compute":
        return {"title": "Digests", "digests": toolkit.compute_hashes(text)}
    if tool == "vigenere":
        key = (request.form.get("key") or "").strip()
        mode = (request.form.get("mode") or "decode").strip()
        if mode not in ("encode", "decode"):
            raise ValueError("Invalid Vigenere mode.")
        try:
            output = toolkit.vigenere(text, key, mode)
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        return {"title": f"Vigenere {mode}", "output": output}
    if tool == "strings":
        return {
            "title": "Strings",
            "strings": toolkit.extract_strings(text.encode("utf-8", errors="replace")),
        }
    if tool == "cyclic":
        raw_length = (request.form.get("key") or "").strip()
        try:
            length = int(raw_length) if raw_length else 200
        except ValueError:
            raise ValueError("Cyclic length must be an integer.") from None
        try:
            output = toolkit.cyclic(length)
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        return {"title": f"Cyclic pattern ({length} bytes)", "output": output}
    if tool == "cyclic-offset":
        needle = (request.form.get("key") or "").strip() or text.strip()
        try:
            offset = toolkit.cyclic_offset(needle)
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        return {"title": "Cyclic offset", "output": str(offset)}
    if tool == "pack":
        value = (request.form.get("key") or "").strip() or text.strip()
        try:
            packed = toolkit.pack(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        return {
            "title": f"Packed little-endian ({packed['width']}-bit)",
            "output": f"escaped: {packed['escaped']}\nhex:     {packed['hex']}",
        }
    raise ValueError("Unknown toolkit action.")
