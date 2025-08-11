# COPILOT\_BRIEF.md

## Scope

Refactor **`src/lib/components/chat/CourseChat.svelte`** to keep the **same UI/UX** as the main chat while **reducing functionality to:**

* **Text input → streamed assistant output**
* **Code Interpreter (keep)**
* **Everything else OFF**: audio/TTS, uploads, images, image generation, web search, tool pickers, multi‑model, actions

Additionally, **force a fixed model** for each course (read from the course record). If the course model is missing or unavailable, render a tiny inline **session‑only** model picker (populated from `/api/models`) and bind that choice to the current session (do **not** mutate the course in storage).

---

## Non‑Goals

* No backend schema or API changes
* No test/QA files
* No feature re‑additions beyond Code Interpreter

---

## Design & Runtime Notes

* Do browser‑only work inside `onMount` and guard any DOM/localStorage usage with `$app/environment.browser`.
* Streaming remains via `ReadableStream.getReader()` + `TextDecoder` to progressively append assistant deltas.
* Use **`GET /api/models`** for the **aggregated** model inventory when a session‑only fallback is needed (do not call provider‑specific endpoints from this UI).
* Keep visual parity with the main chat by reusing the existing container/grid/typography classes and the same **Navbar → Messages → MessageInput** stack.

---

## Task 0 — Prep (no code yet)

**Limit the scope to a single file:**

* Work **only** in `src/lib/components/chat/CourseChat.svelte`.
* Keep **Navbar**, **Messages**, and **MessageInput**, preserving the outer container classes so sizing (max‑width, paddings, input bar height) matches the main chat.

**Acceptance:** File targeted; no other files touched.

---

## Task 1 — Bind the Course Model (Fixed)

1. In `onMount`, read `courseId` from route params (`$page.params`). Fetch the course (use the existing classroom API/helper). Then:

   * Set `atSelectedModel` to `$models.find(m => m.id === course.model_id)`.
   * Set `selectedModels = [atSelectedModel.id]`.
   * Hydrate `params` from course when present:

     * `params.temperature = course.temperature`
     * `params.max_tokens = course.max_tokens`
     * `params.system = course.system_prompt`
     * `params.kb_id = course.kb_id`
2. Hide the navbar model selector: `<Navbar … showModelSelector={false} />`.
3. If the course has **no model** or it isn’t in `$models`, fetch **`/api/models`**, render a compact inline `<select>` banner above the composer ("Select a model for this session"). On choose → set `atSelectedModel` and `selectedModels = [id]`. **Session‑only**; do not update the course record.

**Acceptance:** `atSelectedModel` is always set before sending; otherwise the inline picker appears and sets it.

---

## Task 2 — Strip to **Text + Code Interpreter**

1. **Remove/disable** all non‑text features:

   * Upload flows & handlers (`web`, `youtube`, `google-drive`) and related imports/helpers/state (`files`, `chatFiles`, and their validations)
   * Audio/TTS (hidden `<audio>`, speak buttons, TTS events)
   * Images, image generation, web search, tool selection, multi‑model actions
   * The `ChatControls` import and its bottom JSX block
2. **Keep**:

   * `codeInterpreterEnabled` state and any existing UI toggle for it
   * `Navbar`, `Messages`, and `MessageInput` visual parity
3. **MessageInput props**:

   * **Keep:** `bind:prompt`, `bind:autoScroll`, `bind:atSelectedModel`, `on:submit`
   * **Drop:** `on:upload`, `bind:files`, `bind:selectedToolIds`, `bind:selectedFilterIds`, `bind:imageGenerationEnabled`, `bind:webSearchEnabled`, `toolServers`, etc.

**Acceptance:** Composer shows a clean text area + Send; Code Interpreter toggle remains; no upload/voice/image/web‑search actions visible or functional.

---

## Task 3 — Force a Single‑Model Send Pipeline

1. In `submitPrompt` / `sendPrompt`:

   * Compute **only**: `const selectedModelIds = atSelectedModel ? [atSelectedModel.id] : [];`
   * If empty → toast “Model not selected” and block send.
   * Remove/bypass multi‑model loops and any regeneration logic predicated on multiple models.
2. In `sendPromptSocket`, always call `generateOpenAIChatCompletion` with:

   ```ts
   model: atSelectedModel.id,
   stream: true,
   messages, // text only
   params: { ...params }, // include temperature, max_tokens, system, kb_id if present
   features: {
     image_generation: false,
     web_search: false,
     code_interpreter: codeInterpreterEnabled,
     memory: $settings?.memory ?? false
   },
   // model_item: $models.find(m => m.id === atSelectedModel.id) if the API expects it
   ```
3. Keep the existing streaming reader logic (append deltas to the last assistant bubble).

**Acceptance:** Every send uses exactly one model (the course model or the session‑picked fallback) and streams correctly.

---

## Task 4 — Minimal UI Parity with Main Chat

* Preserve the current container/grid/spacing classes so CourseChat matches the sizing and rhythm of the main chat.
* Keep header chips (Model, Temp, Max Tokens, Knowledge, System Prompt view/edit). Show the live `atSelectedModel.id` in a compact badge next to “Course Chat”.
* The optional classroom side panel may remain unchanged; it is independent of chat behavior.

**Acceptance:** The column width, paddings, and composer height mirror the main chat; controls are simplified.

---

## Task 5 — Inline Fallback Model Picker (Only if Needed)

* Triggered when the course’s `model_id` is missing or not found in `$models`.
* Fetch `/api/models` (aggregated list), filter to non‑embedding chat models.
* Render a small banner with a `<select>`; once a model is chosen, set `atSelectedModel` and `selectedModels = [id]` and hide the banner. Do **not** mutate the course record.

**Acceptance:** Users can proceed without editing the course; the chosen model is used for the current session.

---

## Task 6 — Cleanup & SSR Safety

* Delete unused imports (uploads/retrieval/tools/ChatControls/audio) and dead code.
* Ensure all browser‑only logic runs inside `onMount`. Guard DOM, `localStorage`, and `window` usage with `$app/environment.browser`.

**Acceptance:** No SSR/hydration warnings in console; no unused imports remain.

---

## Manual Acceptance (Runbook)

* **Course has valid model** → opening CourseChat shows no model warning; typing and sending streams back; Code Interpreter available.
* **Course missing model** → inline session picker appears; after selecting a model, sending streams back; the course DB is unchanged.
* Composer is text‑only; no uploads/audio/images/web search.
* Network shows only `GET /api/models` (fallback) and `POST /api/chat/completions` with `stream: true`.

---

## Notes for Copilot Agent

* Keep diffs **localized to this single file**.
* If `MessageInput.svelte` still renders extra icons by default, hide them via existing props/flags; do **not** re‑enable non‑text features.
* Do not modify backend endpoints or other components.

---
