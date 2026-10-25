import json, mimetypes, os, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Tried in order; the first one that works is remembered for the rest of the run.
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash",
          "gemini-3-flash-preview", "gemini-2.5-flash-lite"]
_good = {"model": None}

SYSTEM = """You are a visual investigation agent for images of monuments, historical
structures and cultural sites. Work evidence-first: list visible clues, then form
hypotheses, then decide. Never force an exact answer: if evidence is insufficient,
give the region/style/period only and say so. Never invent history.
Keep three categories strictly separate:
- OBSERVED: directly visible in the image
- INFERRED: your reasoning from the observations
- VERIFIED: facts confirmed through web search (cite sources)
Use web search sparingly, only to verify a specific hypothesis suggested by the clues.
Authenticity (real photo vs AI-generated) is probabilistic; give a confidence."""

PROMPT = """Investigate this image. Reply with ONLY a JSON object with these keys:
image_summary (str), primary_subject (str),
observed_clues (list of str), inferred_points (list of str),
probable_location {country, region, locality} (use "Unknown" where not supportable),
identified_landmark (str or "Not confidently identified"),
location_confidence {level: High|Medium|Low, score: 0-100, why: str},
alternative_hypotheses (list of str),
authenticity {verdict: Likely real|Uncertain|Likely AI-generated, confidence: 0-100, signals: list of str},
historical_context (str, only verified facts, else "Not determined"),
verified_facts (list of str),
reasoning (str linking clues to conclusions),
additional_observations (list of str),
sources (list of URLs)."""


def _grounding_urls(resp):
    urls = []
    try:
        for ch in resp.candidates[0].grounding_metadata.grounding_chunks or []:
            if ch.web and ch.web.uri:
                urls.append(ch.web.uri)
    except Exception:
        pass
    return urls


def _generate(contents, use_search, json_mode):
    """Tries each model in turn. Returns (text, urls). Raises if all fail."""
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=8000)
    if use_search:
        cfg.tools = [types.Tool(google_search=types.GoogleSearch())]
    elif json_mode:
        cfg.response_mime_type = "application/json"  # can't be combined with search

    order = ([_good["model"]] if _good["model"] else []) + \
            [m for m in MODELS if m != _good["model"]]
    last = None
    for model in order:
        for attempt in range(2):
            try:
                resp = client.models.generate_content(model=model, contents=contents, config=cfg)
                text = resp.text or ""
                if not text.strip():
                    last = RuntimeError(f"{model} returned empty text")
                    print(f"  {model}: empty reply, trying next model")
                    break
                _good["model"] = model
                return text, _grounding_urls(resp)
            except Exception as e:
                last = e
                msg = str(e)
                print(f"  {model}: {msg[:110]}")
                if "404" in msg or "NOT_FOUND" in msg:
                    break                      # model unavailable -> next model
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    if attempt == 0:
                        time.sleep(10)         # one short wait, then next model
                        continue
                    break
                break                          # any other error -> next model
    raise last


def _call(contents, use_search, json_mode=False):
    """Search first; if it fails or is empty, fall back to no-search."""
    if use_search:
        try:
            text, urls = _generate(contents, True, json_mode)
            if text.strip():
                return text, urls
        except Exception as e:
            print("  search unavailable, retrying without search:", str(e)[:100])
    return _generate(contents, False, json_mode)


def _parse(text, urls):
    try:
        r = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:
        r = {"image_summary": text}
    r["sources"] = list(dict.fromkeys((r.get("sources") or []) + urls))
    return r

def analyze(data: bytes, media_type: str, use_search=False):
    """Returns (report_dict, history). History keeps the image for follow-ups."""
    user = types.Content(role="user", parts=[
        types.Part.from_bytes(data=data, mime_type=media_type),
        types.Part.from_text(text=PROMPT)])
    text, urls = _call([user], use_search, json_mode=True)
    history = [user, types.Content(role="model", parts=[types.Part.from_text(text=text or "{}")])]
    return _parse(text, urls), history


def analyze_file(path, use_search=False):
    mt = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        return analyze(f.read(), mt, use_search)


def follow_up(history, question, use_search=False):
    history.append(types.Content(role="user", parts=[types.Part.from_text(
        text=question + "\n(Answer concisely, refer to the image and your earlier "
        "findings; state uncertainty honestly.)")]))
    ans, _ = _call(history, use_search, json_mode=False)
    history.append(types.Content(role="model", parts=[types.Part.from_text(text=ans)]))
    return ans


def to_markdown(r):
    g = lambda k, d="N/A": r.get(k, d)
    loc = g("probable_location", {}) or {}
    conf = g("location_confidence", {}) or {}
    auth = g("authenticity", {}) or {}
    bl = lambda xs: "\n".join(f"- {x}" for x in (xs or [])) or "- N/A"
    return f"""### Image Summary
{g('image_summary')}

**Primary Subject:** {g('primary_subject')}
**Identified Landmark:** {g('identified_landmark')}

### Probable Location
{loc.get('country','Unknown')} / {loc.get('region','Unknown')} / {loc.get('locality','Unknown')}
**Confidence:** {conf.get('level','?')} ({conf.get('score','?')}/100) - {conf.get('why','')}

### Observed (directly visible)
{bl(r.get('observed_clues'))}

### Inferred
{bl(r.get('inferred_points'))}

### Verified (external sources)
{bl(r.get('verified_facts'))}

### Alternative Hypotheses
{bl(r.get('alternative_hypotheses'))}

### Authenticity
**{auth.get('verdict','?')}** ({auth.get('confidence','?')}% confidence)
{bl(auth.get('signals'))}

### Historical & Cultural Context
{g('historical_context')}

### Reasoning & Evidence
{g('reasoning')}

### Additional Observations
{bl(r.get('additional_observations'))}

### Sources
{bl(r.get('sources'))}
"""