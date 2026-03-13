/**
 * Annotations module — notes and tags CRUD for the IOC detail page.
 *
 * Wires up:
 * - Notes: textarea + save button, POSTs to /api/ioc/{type}/{value}/notes
 * - Tags: text input + add button (or Enter key), POST to /api/ioc/{type}/{value}/tags
 * - Tag delete: X button on each tag pill, DELETE to /api/ioc/{type}/{value}/tags/{tag}
 *
 * CSRF: Reads the CSRF token from <meta name="csrf-token"> and sends it via
 * X-CSRFToken header on every mutating request. Flask-WTF CSRFProtect accepts
 * this header automatically for JSON requests (SEC-10).
 *
 * DOM safety: Uses createElement + textContent only, never innerHTML (SEC-08).
 */

/** Read the CSRF token from the <meta name="csrf-token"> element. */
function getCSRFToken(): string {
  const meta = document.querySelector<HTMLMetaElement>(
    'meta[name="csrf-token"]'
  );
  return meta ? meta.content : "";
}

/** Read the IOC identity from the .page-ioc-detail element data attributes. */
function getPageIOC(): { iocType: string; iocValue: string } | null {
  const el = document.querySelector<HTMLElement>(".page-ioc-detail");
  if (!el) return null;
  const iocType = el.dataset.iocType ?? "";
  const iocValue = el.dataset.iocValue ?? "";
  if (!iocType || !iocValue) return null;
  return { iocType, iocValue };
}

/** POST notes to /api/ioc/{type}/{value}/notes. */
async function saveNotes(
  iocType: string,
  iocValue: string,
  notes: string
): Promise<{ ok: boolean; notes: string }> {
  const response = await fetch(
    `/api/ioc/${encodeURIComponent(iocType)}/${encodeURIComponent(iocValue)}/notes`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ notes }),
    }
  );
  return response.json() as Promise<{ ok: boolean; notes: string }>;
}

/** POST a new tag to /api/ioc/{type}/{value}/tags. */
async function addTag(
  iocType: string,
  iocValue: string,
  tag: string
): Promise<{ ok: boolean; tags: string[] }> {
  const response = await fetch(
    `/api/ioc/${encodeURIComponent(iocType)}/${encodeURIComponent(iocValue)}/tags`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ tag }),
    }
  );
  return response.json() as Promise<{ ok: boolean; tags: string[] }>;
}

/** DELETE a tag from /api/ioc/{type}/{value}/tags/{tag}. */
async function deleteTag(
  iocType: string,
  iocValue: string,
  tag: string
): Promise<{ ok: boolean; tags: string[] }> {
  const response = await fetch(
    `/api/ioc/${encodeURIComponent(iocType)}/${encodeURIComponent(iocValue)}/tags/${encodeURIComponent(tag)}`,
    {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCSRFToken(),
      },
    }
  );
  return response.json() as Promise<{ ok: boolean; tags: string[] }>;
}

/**
 * Render a single tag pill into the container.
 *
 * DOM safety: uses createElement + textContent only (SEC-08).
 */
function renderTagPill(
  tag: string,
  container: HTMLElement,
  iocType: string,
  iocValue: string
): void {
  const pill = document.createElement("span");
  pill.className = "tag-pill";
  pill.dataset.tag = tag;

  const label = document.createTextNode(tag + " ");
  pill.appendChild(label);

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "tag-remove";
  deleteBtn.setAttribute("aria-label", `Remove tag ${tag}`);
  deleteBtn.textContent = "\u00d7"; // x

  deleteBtn.addEventListener("click", () => {
    deleteTag(iocType, iocValue, tag)
      .then(() => {
        pill.remove();
      })
      .catch(() => {
        // Silent fail — pill stays in place
      });
  });

  pill.appendChild(deleteBtn);
  container.appendChild(pill);
}

/**
 * Initialise annotations module.
 *
 * Does nothing if .page-ioc-detail is absent (not on detail page).
 */
export function init(): void {
  const pageEl = document.querySelector<HTMLElement>(".page-ioc-detail");
  if (!pageEl) return;

  const ioc = getPageIOC();
  if (!ioc) return;
  const { iocType, iocValue } = ioc;

  // ---- Notes ----------------------------------------------------------------
  const notesTextarea = document.getElementById(
    "ioc-notes"
  ) as HTMLTextAreaElement | null;
  const saveNotesBtn = document.querySelector<HTMLButtonElement>(
    ".btn-save-notes, .save-notes-btn"
  );

  if (notesTextarea && saveNotesBtn) {
    saveNotesBtn.addEventListener("click", () => {
      const notes = notesTextarea.value;
      saveNotes(iocType, iocValue, notes)
        .then(() => {
          // Brief "Saved" feedback via CSS class
          saveNotesBtn.classList.add("btn--saved");
          setTimeout(() => saveNotesBtn.classList.remove("btn--saved"), 1500);
        })
        .catch(() => {
          // Silent fail
        });
    });
  }

  // ---- Tags -----------------------------------------------------------------
  const tagPillsContainer = document.getElementById("tag-pills");
  const tagInput = document.getElementById(
    "tag-input"
  ) as HTMLInputElement | null;
  const tagAddBtn = document.querySelector<HTMLButtonElement>(
    ".btn-add-tag, [aria-label='Add tag']"
  );

  if (tagPillsContainer) {
    // Render existing tags from data-tags attribute (JSON list set by Jinja2)
    const existingTagsRaw = pageEl.dataset.tags ?? "[]";
    let existingTags: string[] = [];
    try {
      existingTags = JSON.parse(existingTagsRaw) as string[];
    } catch {
      existingTags = [];
    }

    // Clear server-rendered static pills to avoid duplicates with JS-rendered ones
    while (tagPillsContainer.firstChild) {
      tagPillsContainer.removeChild(tagPillsContainer.firstChild);
    }

    existingTags.forEach((tag) => {
      renderTagPill(tag, tagPillsContainer, iocType, iocValue);
    });

    // Wire add button and Enter key
    const doAddTag = (): void => {
      if (!tagInput) return;
      const tag = tagInput.value.trim();
      if (!tag) return;

      addTag(iocType, iocValue, tag)
        .then((result) => {
          if (result.ok) {
            renderTagPill(tag, tagPillsContainer, iocType, iocValue);
            tagInput.value = "";
          }
        })
        .catch(() => {
          // Silent fail
        });
    };

    if (tagAddBtn) {
      tagAddBtn.addEventListener("click", doAddTag);
    }

    if (tagInput) {
      tagInput.addEventListener("keydown", (e: KeyboardEvent) => {
        if (e.key === "Enter") {
          e.preventDefault();
          doAddTag();
        }
      });
    }
  }
}
