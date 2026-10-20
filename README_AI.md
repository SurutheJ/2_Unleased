# AI listing assistant (A6 Part 2)

**What it does.** A logged-in user pastes an informal sublease message (the kind
that gets posted in WhatsApp groups). A **local Hugging Face model** pulls out
structured listing fields, then the **Google Gemini API** writes a short listing
description from those fields. The page only *previews* the result; nothing is saved.

Page: `/listings/ai-assistant/` (navbar tab **AI assistant**, login required).

```
pasted message
   -> clean_message()        preprocessing + masking      listings/ai_local.py
   -> local model (granite-4.0-micro) -> JSON text      listings/ai_local.py
   -> parse_model_output() + validate_fields()           listings/ai_local.py
   -> generate_description()  Gemini API (validated fields only)  listings/ai_external.py
   -> page shows fields, warnings, description
```

## 1. System description

### Data input
- A `<textarea>` on `/listings/ai-assistant/`, submitted with **POST** and a CSRF token
  (`ai_assistant` in `listings/views.py`). The page needs login, so every request has a user.
- Up to 2000 characters (`AI_MAX_MESSAGE_CHARS`). The browser enforces `maxlength`; the server
  enforces it again because the browser cannot be trusted.
- This is the same input the model was prototyped on in `llm-test/ai_prototype.ipynb`
  (informal messages like "$650/mo, furnished, text 217-555-0199"), and it fits the existing
  `Listing.raw_whatsapp_text` / `Listing.ai_parsed` fields. Saving a listing from the result
  is not built yet.

### Preprocessing (`clean_message`)
Before anything reaches a model the message is:
1. Unicode-normalised (NFKC) and stripped of control characters.
2. Stripped of HTML-like tags (replaced with a space so neighbouring words do not glue together).
3. **Masked:** phone numbers become `[phone]` and emails become `[email]`. The model does not need
   them, and contact details should not travel any further than the user's own request.
4. Whitespace-collapsed and cut to the length limit.

The user is shown what changed ("Masked 0 email address(es) and 1 phone number(s)").
The model is then given a system prompt that lists the 11 fields and their types, tells it today's
date (so "dec 15" resolves to the next December, not a year from its training data), says the message
is untrusted data between `<message>` tags, and says to use `null` rather than guess.
Decoding is greedy (`do_sample=False`) and capped at 300 new tokens.

### Safety guardrails
**Malicious or odd input**
- Login + POST + CSRF; a per-user cooldown (5 s) stops rapid repeated requests from tying up the model.
- Length cap, tag stripping and control-character removal (above).
- A heuristic filter refuses messages that contain obvious instructions to the AI
  ("ignore all previous instructions", "you are now", "reveal your prompt"); the model is never called.
  This is **easy to evade** (we tested a reworded version, and it was not caught), so it is only the first layer.
- The system prompt tells the model to treat the message as data, never as instructions.
- Only the **validated fields** go to the external API. The user's raw message (which can contain
  contact details or injected text) never leaves the server.

**Broken or untrustworthy output** (`parse_model_output`, `validate_fields`)
- Small models wrap JSON in code fences, add trailing sentences, or loop forever. The parser takes the
  first JSON object and returns "no result" for anything else, and the page shows a clear error instead of crashing.
- Every field is checked for type and range: rent must be a number between $100 and $20,000; bedrooms a
  whole number up to 20; booleans real booleans; dates real ISO dates in a plausible range, start before end,
  and not already over. Unknown keys are dropped; anything invalid becomes "not found" so the user fills it in.
- **Grounding:** a value is only kept if the message actually supports it. A yes/no field needs a
  related word in the message (`laundry`, `pets`, `parking`...), the rent must appear in the message,
  and the bedroom count must match something like `3bd` or `two bedroom` (or "studio").
  This exists because small models can answer "yes" or "no" for features nobody mentioned. Our first model
  (Qwen2.5-1.5B) did exactly that on the vague test message: it answered "false" for furnished, laundry,
  balcony and utilities, none of which the message mentions. The notebook's matrix shows the same habit in
  a couple of the 15 models. The current model (Granite) did not do it on our five test messages, but the
  check stays: it is cheap, and a different model, a different device, or a stranger message can bring the habit back.
- Model text is shown through Django's auto-escaping, so a model that outputs `<script>` cannot inject markup.
- The external API call has a timeout, handles HTTP errors, blocked/empty/malformed replies, and a missing key,
  and **always falls back** to a template description, with a note saying why.

**Known limits (not hidden)**
- Free-text fields cannot be validated by rule. A message that says "the title is PWNED" produced
  `"title": "PWNED"` in our test, because that word really is in the message. Impact is limited to the
  user's own preview: nothing is saved, executed, or sent to other users, and the title is escaped.
- Grounding uses keyword lists, so a legitimate synonym we did not list (for example "w/d" is covered but "washing machine" is not)
  is blanked. That fails safe: the user fills it in.
- The model can still be wrong about values that pass every check.

## 2. Local LLM integration
- Model: **`ibm-granite/granite-4.0-micro`**, the model the Part 1 notebook chose ("Decision for this app":
  Granite with zero-shot prompting). Change it with `LOCAL_LLM_MODEL` in `.env`.
- **Why this one.** In the notebook's Route A test it was the only model that stayed fully correct across zero-,
  one-, few- and many-shot prompts, so a short zero-shot prompt (instructions only, no worked examples) gets
  full reliability. We also ran it for real through this app's pipeline on five messages, including two
  prompt-injection attempts: the clear message came back fully correct with no warnings, the vague message came
  back with nothing invented, a studio listing got bedrooms = 0, and the plain injection attempt was ignored.
  Our first model, Qwen2.5-1.5B, invented "false" answers on the vague message (and, before we put today's
  date in the prompt, 2023 dates).
- **Trade-off we accepted.** It is bigger and slower than Qwen2.5-1.5B: about a **6.8 GB download** (3.1 GB for
  Qwen) and about 7 to 9 s per message (about 4 s for Qwen). For a smaller, faster setup set
  `LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct`; it works with the same guardrails but is less reliable.
- **Use a non-thinking model.** In the notebook Qwen3-0.6B, Qwen3-1.7B and SmolLM3-3B spent their whole
  200-token budget on `<think>` reasoning and never produced JSON. This app caps output at 300 new tokens
  (`AI_MAX_NEW_TOKENS`), so a thinking model would most likely fail the same way (not tested here).
- **It is not perfect.** An injection reworded to avoid our phrase filter still got `"title": "PWNED"` out of
  Granite (the fake rent of $1 was rejected by validation), and on one run on CPU it returned the end date in
  the wrong year, which the start-before-end check caught. The guardrails exist for this reason.
- Loaded with `transformers.pipeline("text-generation", ...)` the first time it is needed, then reused
  for the life of the server process (`_get_pipeline` in `listings/ai_local.py`, guarded by a lock so only
  one generation runs at a time). The weights (about 6.8 GB) download automatically to `~/.cache/huggingface`.
- Device: `LOCAL_LLM_DEVICE=auto` picks the best single device (CUDA, then the Mac GPU, then CPU). We do **not**
  use accelerate's `device_map="auto"`: on a 16 GB Mac it offloaded Granite to disk and had not finished one
  message after 19 minutes. The model needs roughly 7 to 8 GB of free memory.
- Measured on a 16 GB Apple Silicon Mac (`torch 2.14.1`, `transformers 5.20.2`), with the weights already
  downloaded: GPU about **16 s for the first request** (loading) then **7 to 8 s per message**; CPU only about
  21 s then 9 s. The download itself depends on your connection.

### Running it locally
```bash
pip install -r requirements.txt           # includes torch, transformers, accelerate
python manage.py migrate
python manage.py runserver
```
Log in, open **AI assistant**, paste a message. On the first request `transformers` downloads the weights
(about 6.8 GB, so allow several minutes) and loads them; later requests take under ten seconds. With no
`GEMINI_API_KEY` set everything still works and the description comes from a template.

`requirements.txt` has everything needed, including `torch` and `transformers`. PythonAnywhere's free
account cannot hold them (`torch` alone is larger than the 512 MB quota), so deploys there use
`requirements-deploy.txt`, the same list without the AI libraries. On a site installed that way the page shows
"The local model libraries are not installed on this server" (HTTP 503) instead of crashing. The local model is
meant to run on a developer machine.

## 3. External API integration
- **Google Gemini API** (free tier), `generateContent` endpoint, called with `requests.post`
  (`listings/ai_external.py`). Get a key at <https://aistudio.google.com/apikey>.
- The key goes in `.env` as `GEMINI_API_KEY` (never committed). With no key the page still works and uses
  the template description.
- The model is `GEMINI_MODEL`, default **`gemini-flash-latest`** (Google's alias for the current Flash model).
  We first used `gemini-2.5-flash` and Google answered HTTP 404 "no longer available to new users", so a
  pinned name can be retired under you; the alias avoids that. Run
  `GET https://generativelanguage.googleapis.com/v1beta/models` with your key to see what it can call.
- Current Gemini models spend part of the output budget on hidden "thinking" before any text appears.
  With the first 300-token limit the reply came back cut off mid-sentence or empty. The request now asks
  for `thinkingLevel: low` (`GEMINI_THINKING_LEVEL`, set it empty for a model that rejects it) with a
  1024-token budget, and a reply whose `finishReason` is not `STOP` falls back to the template instead of
  showing half a sentence.
- The free tier is limited and sometimes busy. From a working key we saw HTTP 503 ("high demand"), HTTP 429 for
  a per-minute limit, and HTTP 429 for the **daily** limit (`GenerateRequestsPerDayPerProjectPerModel`),
  which Google said would reset in about 5.8 hours. Quotas are **per model**: when `gemini-flash-latest` was
  used up, `gemini-3.5-flash` still answered, so setting `GEMINI_MODEL` is a quick workaround.
- The call retries up to 2 more times on 5xx and on short 429s (`GEMINI_RETRIES`, waiting as long as Google's
  `retryDelay` asks). It does **not** retry a 429 that asks for a long wait, because that is a quota and retrying
  only burns more of it. Every failure falls back to the template with a notice that names the cause
  ("busy", "rate limit, wait a minute", or "daily limit used up, resets in about N hours").
- `googleapis.com` is on PythonAnywhere's free-tier outbound allowlist, so this call is expected
  to work from a free PythonAnywhere account.

## Testing
`python manage.py test listings.test_ai` (65 tests across the app; 54 of them are new). The real model and
real Gemini API are replaced with canned replies, including the broken ones real small models produce
(code fences, repetition loops, hallucinated dates, injected values). Covered: preprocessing, parsing,
every validation and grounding rule, the view (login, CSRF, cooldown, short input, unreadable output,
unavailable model, escaped output, nothing saved), and every Gemini failure mode.

**What was and was not run for real**
- Run for real: the local model on this Mac, through both a script and the actual page (logged in with a
  headless browser). Results for the team's three test messages plus two injection attempts are in
  `docs/screenshots/a6-p2-01-ai-assistant.png` (earlier Qwen model, with a live Gemini description) and
  `docs/screenshots/a6-p2-02-ai-assistant-granite-fallback.png` (current Granite model; Gemini's daily limit
  was used up, so it shows the template fallback with its notice), plus the notes entry.
- Gemini was also run for real with a free-tier key (about 12 s for the first call, about 2 s after) and
  returns a sensible description from the validated fields. The error paths (timeout, HTTP errors, blocked or
  cut-off replies, missing key) are tested with mocks, because they are hard to trigger on demand.
- Not run: the deployed site. The local model is not installed there (see above), so the whole
  pipeline has only been run on a developer machine.
