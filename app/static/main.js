/**
 * SentinelX — main.js
 *
 * Minimal, CSP-compliant JavaScript for the IOC extractor UI.
 * No inline event handlers — all listeners are attached from this external file.
 *
 * Features:
 * - Disable submit button when textarea is empty
 * - Clear button resets textarea and re-disables submit
 * - Clipboard copy for IOC values via navigator.clipboard API
 */

(function () {
    "use strict";

    // ---- Submit button: disable when textarea is empty ----

    function initSubmitButton() {
        var form = document.getElementById("analyze-form");
        if (!form) return;

        var textarea = document.getElementById("ioc-text");
        var submitBtn = document.getElementById("submit-btn");
        var clearBtn = document.getElementById("clear-btn");

        if (!textarea || !submitBtn) return;

        function updateSubmitState() {
            submitBtn.disabled = textarea.value.trim().length === 0;
        }

        textarea.addEventListener("input", updateSubmitState);

        // Also handle paste events (browser may not fire "input" immediately)
        textarea.addEventListener("paste", function () {
            // Defer until after paste content is applied
            setTimeout(updateSubmitState, 0);
        });

        // Initial state (page load with pre-filled content)
        updateSubmitState();

        // ---- Clear button ----
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                textarea.value = "";
                updateSubmitState();
                textarea.focus();
            });
        }
    }

    // ---- Clipboard copy for IOC values ----

    function initCopyButtons() {
        var copyButtons = document.querySelectorAll(".copy-btn");

        copyButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var value = btn.getAttribute("data-value");
                if (!value) return;

                if (!navigator.clipboard) {
                    // Fallback for non-HTTPS or older browsers
                    fallbackCopy(value, btn);
                    return;
                }

                navigator.clipboard.writeText(value).then(function () {
                    showCopiedFeedback(btn);
                }).catch(function () {
                    fallbackCopy(value, btn);
                });
            });
        });
    }

    function showCopiedFeedback(btn) {
        var original = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(function () {
            btn.textContent = original;
            btn.classList.remove("copied");
        }, 1500);
    }

    function fallbackCopy(text, btn) {
        // Create a temporary textarea, select its content, and copy
        var tmp = document.createElement("textarea");
        tmp.value = text;
        tmp.style.position = "fixed";
        tmp.style.top = "-9999px";
        tmp.style.left = "-9999px";
        document.body.appendChild(tmp);
        tmp.focus();
        tmp.select();
        try {
            document.execCommand("copy");
            showCopiedFeedback(btn);
        } catch (e) {
            // Copy failed silently — user can still manually select the value
        } finally {
            document.body.removeChild(tmp);
        }
    }

    // ---- Initialise on DOM ready ----

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            initSubmitButton();
            initCopyButtons();
        });
    } else {
        // DOM already ready (script is deferred or loaded late)
        initSubmitButton();
        initCopyButtons();
    }

}());
