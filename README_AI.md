# AI listing assistant (A6 Part 2)

**What it does.** A logged-in user pastes an informal sublease message (the kind
that gets posted in WhatsApp groups). A **local Hugging Face model** pulls out
structured listing fields, then the **Google Gemini API** writes a short listing
description from those fields. The page only *previews* the result; nothing is saved.

Page: `/listings/ai-assistant/` (navbar tab **AI assistant**, login required).

```
pasted message
   -> clean_message()        preprocessing + masking      listings/ai_local.py
   -> local model (Qwen2.5-1.5B-Instruct) -> JSON text   listings/ai_local.py
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
  This exists because the team's own matrix test (`llm-test/results.json`) and our runs showed small
  models answering "yes" or "no" for features nobody mentioned.
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
- Model: **`Qwen/Qwen2.5-1.5B-Instruct`**, chosen in the Part 1 lab (`llm-test/ai_prototype.ipynb`) as the
  best size/quality trade-off for this task. Change it with `LOCAL_LLM_MODEL` in `.env`.
- Loaded with `transformers.pipeline("text-generation", ...)` the first time it is needed, then reused
  for the life of the server process (`_get_pipeline` in `listings/ai_local.py`, guarded by a lock so only
  one generation runs at a time). The weights (about 3 GB) download automatically to `~/.cache/huggingface`.
- Measured on an Apple Silicon Mac ( `torch 2.14.1`, `transformers 5.20.2`): about **95 s for the
  first request** (download already cached; loading and warm-up), then **3 to 4 s per message**.

### Running it locally
```bash
pip install -r requirements.txt
pip install -r requirements-ai.txt        # torch + transformers + accelerate (large)
python manage.py migrate
python manage.py runserver
```
Log in, open **AI assistant**, paste a message.

`requirements-ai.txt` is separate on purpose: `torch` is far bigger than PythonAnywhere's 512 MB free
quota, so putting it in `requirements.txt` would break deploys. Consequence: **on a deployed site
without those libraries the page shows "The local model libraries are not installed on this server"**
(HTTP 503) instead of crashing. The local model is meant to run on a developer machine.

## 3. External API integration
- **Google Gemini API** (free tier), `generateContent` endpoint, called with `requests.post`
  (`listings/ai_external.py`). Get a key at <https://aistudio.google.com/apikey>.
- The key goes in `.env` as `GEMINI_API_KEY` (never committed); the model name is `GEMINI_MODEL`
  (default `gemini-2.5-flash`). With no key the page still works and uses the template description.
- It is a **hybrid pipeline**: the local model reads and validates the messy text, and Gemini only
  turns the clean fields into a friendly 2-3 sentence description. The prompt tells Gemini to use only
  those facts and to treat the values as data.
- `googleapis.com` is on PythonAnywhere's free-tier outbound allowlist, so this call is expected
  to work from a free PythonAnywhere account.

## Testing
`python manage.py test listings.test_ai` (57 tests across the app; 46 of them are new). The real model and
real Gemini API are replaced with canned replies, including the broken ones real small models produce
(code fences, repetition loops, hallucinated dates, injected values). Covered: preprocessing, parsing,
every validation and grounding rule, the view (login, CSRF, cooldown, short input, unreadable output,
unavailable model, escaped output, nothing saved), and every Gemini failure mode.

**What was and was not run for real**
- Run for real: the local model on this Mac, through both a script and the actual page (logged in with a
  headless browser). Results for the team's three test messages plus two injection attempts are in
  `docs/screenshots/a6-p2-01-ai-assistant.png` and the notes entry.
- **Not run for real: the Gemini call.** No API key was available while building this, so only the
  request shape, error handling and fallback are tested (with mocks). Confirm it once with a real key.
