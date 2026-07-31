"""Per-category methodology checklists for CTF challenges.

Static, offline first-step hints shown on challenge pages. These are
methodology prompts, not solutions.
"""
from __future__ import annotations

HINTS: dict[str, list[str]] = {
    "web": [
        "Enumerate directories/vhosts (gobuster/ffuf) and read every response body.",
        "Check cookies, JWTs, and session handling for tampering.",
        "Probe inputs for injection: SQLi, SSTI, XSS, command injection.",
        "Review JS/source maps for endpoints, secrets, and hidden parameters.",
        "Test IDOR/access-control gaps on object references.",
    ],
    "crypto": [
        "Identify the construction: classical cipher, encoding, or modern primitive.",
        "Try the toolkit: auto-decode, Caesar/XOR brute, hash identification.",
        "Look for key reuse (OTP, ECB penguin, nonce reuse).",
        "Check RSA parameters: small e, common modulus, Wiener's, factordb.",
        "Oracle? Test padding/bit-flipping/length-extension behavior.",
    ],
    "pwn": [
        "checksec first: NX, PIE, canary, RELRO.",
        "Find the bug class: overflow, format string, UAF, off-by-one.",
        "Use cyclic patterns to size offsets; pack addresses little-endian.",
        "Leak before you pivot: GOT/puts for libc, then ret2libc or ret2system.",
        "Script the interaction; keep payloads reproducible.",
    ],
    "rev": [
        "Identify the binary: file type, packing, language/runtime.",
        "Strings and imports before disassembly.",
        "Trace input validation logic; find the success branch.",
        "Consider symbolic/dynamic shortcuts before full manual reversal.",
        "Reimplement the check in Python to derive the flag.",
    ],
    "forensics": [
        "Start with file signature, metadata, and strings — cheapest wins first.",
        "Carve embedded files (binwalk-style) and inspect every layer.",
        "For pcaps: follow streams, extract objects, check DNS exfil.",
        "For memory: enumerate processes, then dig into the interesting one.",
        "Stego? Check LSBs, appended data, and palette anomalies.",
    ],
    "osint": [
        "Pivot on every artifact: usernames, emails, domains, images.",
        "Check EXIF and reverse-search imagery.",
        "Search code repos and paste sites for the identifiers.",
        "Correlate timestamps and time zones across sources.",
        "Document every pivot so the trail is reproducible.",
    ],
    "misc": [
        "Read the description twice — misc challenges hide rules in wording.",
        "Identify the encoding/protocol before automating anything.",
        "Script repetitive interaction instead of manual grinding.",
        "Check for pyjail/sandbox escapes if code execution is offered.",
    ],
    "hardware": [
        "Identify protocols: UART, SPI, I2C, JTAG from the artifacts.",
        "Logic captures: decode with sigrok-style analysis mentally or via export.",
        "Firmware: extract, then treat as a rev/forensics challenge.",
    ],
    "blockchain": [
        "Get the contract source/ABI and identify the trust assumptions.",
        "Classic bugs: reentrancy, tx.origin, weak randomness, access control.",
        "Replay state transitions locally before spending transactions.",
    ],
    "ml": [
        "Understand the model input boundary — what can you control?",
        "Try prompt injection / jailbreak patterns for LLM challenges.",
        "For classifiers: probe adversarial perturbations of the input.",
    ],
}

__all__ = ("HINTS",)


def hints_for(category: str) -> list[str]:
    """Return the methodology checklist for a challenge category."""
    return HINTS.get(category, HINTS["misc"])
