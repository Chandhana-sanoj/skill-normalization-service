import re
from dataclasses import dataclass
from typing import Optional

VERSION_TOKEN = r"v?\d+(?:\.\d+){0,2}\+?"
VERSION_RE = re.compile(rf"^{VERSION_TOKEN}(?:/{VERSION_TOKEN})*$", re.IGNORECASE)
NUMERIC_RE = re.compile(r"^v?\d+(?:\.\d+)*\+?(?:/v?\d+(?:\.\d+)*\+?)*$", re.IGNORECASE)
PAREN_VERSION_RE = re.compile(
    rf"\(\s*({VERSION_TOKEN}(?:\s*(?:,|/|&|\band\b)\s*{VERSION_TOKEN})*)\s*\)",
    re.IGNORECASE,
)
VERSION_SEPARATOR_RE = re.compile(r"\s*(?:,|/|&|\band\b)\s*", re.IGNORECASE)
PAREN_GROUP_RE = re.compile(r"\(([^()]*)\)")
EDGE_PUNCT = "()[]{}<>\"'\u2022*:;!?-\u2013\u2014"
DELIMS = ",;|\n"


@dataclass
class Candidate:
    """One piece of text to send to the normalizer."""

    text: str                      # text sent to the normalizer (version attached)
    skill_id: Optional[object]     # canonical ID if the catalogue matched it, else None
    version: Optional[str] = None


@dataclass(eq=False)
class _Element:
    kind: str
    key: str = ""
    text: str = ""
    skill_id: Optional[object] = None
    version: Optional[str] = None


class MultiSkillExtractor:
    """Splits one skill string into candidates for the existing normalizer.

    1. Parentheses: "Aws (lambda, S3)" -> "Aws", "lambda", "S3". "(8.0)" stays a version.
       "Agile (scrum) Methodology" -> "Agile Methodology", "scrum".
    2. Split on , ; | newline (outside parentheses). Text before a colon is a label:
       only catalogue skills in it are kept.
    3. Per segment: whole segment known -> unchanged; longer than max_segment_words -> unchanged.
    4. Longest-first window scan over aliases/canonical names (one skill ID only).
    5. Ambiguous names (Go, R, 2-letter aliases...) need 2+ matches in the segment and
       connector/filler/edge neighbours (a version after the name is skipped).
    6. A version token right after a matched skill is attached to it.
    7. Connector words (and, with, for...) separate runs. Inside a run:
         0 skills  -> leftover words become one candidate (generic words dropped)
         1 skill   -> if nothing meaningful is left over, just the skill; otherwise the
                      whole run stays ONE candidate (compound skill like "Azure Pipelines")
         2+ skills -> each skill, plus leftover words between them, as separate candidates
    8. Nothing accepted -> original text unchanged. Nothing at all -> original input.
    """

    DEFAULT_AMBIGUOUS = {
        "go", "r", "c", "rust", "ruby", "swift", "dash", "unity", "express",
        "spark", "excel", "ember", "julia", "scala",
    }
    PROFICIENCY = {
        "beginner", "intermediate", "advanced", "basic", "basics", "expert", "familiar",
        "proficient", "proficiency", "strong", "good", "conceptual", "understanding",
        "fundamentals", "concepts", "overview", "familiarity", "exposure",
    }
    GENERIC = {
        "programming", "language", "skills", "skill", "tools", "tool", "framework",
        "development", "developer", "knowledge", "experience", "technologies",
        "project", "projects", "hands-on", "working", "worked", "years", "year",
    }
    CONNECTORS = {
        "and", "with", "for", "using", "including", "plus",
        "in", "on", "of", "or", "to", "also", "the", "a", "an", "as", "&",
    }

    def __init__(self, alias_map, canonical_map, ambiguous_names=None, max_segment_words=15):
        self.ambiguous_names = {n.lower() for n in (ambiguous_names or self.DEFAULT_AMBIGUOUS)}
        self.max_segment_words = max_segment_words
        self.proficiency_words = set(self.PROFICIENCY)
        self.generic_words = set(self.GENERIC)
        self.connectors = set(self.CONNECTORS)

        self.lookup = {}
        for alias, ids in alias_map.items():
            key = self._normalize(alias)
            if key:
                self.lookup.setdefault(key, set()).update(self._as_ids(ids))
        for skill_id, name in canonical_map.items():
            key = self._normalize(name)
            if key:
                self.lookup.setdefault(key, set()).add(skill_id)
        self.max_words = max((len(k.split()) for k in self.lookup), default=1)

    @property
    def filler_words(self):
        """Proficiency words plus generic words."""
        return self.proficiency_words | self.generic_words

    # ---------- helpers ----------
    @staticmethod
    def _as_ids(value):
        # alias_map values may be a collection of IDs or a single ID (int, str, UUID...)
        if isinstance(value, (set, frozenset, list, tuple)):
            return set(value)
        return {value}

    @staticmethod
    def _normalize(text):
        return " ".join(text.strip().lower().split())

    @staticmethod
    def _clean(word):
        return word.strip(EDGE_PUNCT).rstrip(".,")

    @staticmethod
    def _join(keys):
        return " ".join(" ".join(keys).split())

    @staticmethod
    def _format_version(raw_version):
        """Normalize a version list to a comma-separated display value."""
        if not raw_version:
            return None
        versions = [
            re.sub(r"^v(?=\d)", "", part.strip(), flags=re.IGNORECASE)
            for part in VERSION_SEPARATOR_RE.split(raw_version)
            if part.strip()
        ]
        return ", ".join(versions) if versions else None

    def _is_ambiguous(self, phrase):
        text = phrase.lower()
        return " " not in text and (len(text) <= 2 or text in self.ambiguous_names)

    def _find_match(self, keys, start):
        max_end = min(len(keys), start + self.max_words)
        for end in range(max_end, start, -1):
            ids = self.lookup.get(self._normalize(" ".join(keys[start:end])))
            if ids and len(ids) == 1:
                return end, next(iter(ids))
        return None

    def _bounded(self, keys, start, end):
        edge = self.connectors | self.filler_words
        left_ok = start == 0 or keys[start - 1].lower() in edge
        right = end
        if right < len(keys) and VERSION_RE.match(keys[right]):
            right += 1
        right_ok = right == len(keys) or keys[right].lower() in edge
        return left_ok and right_ok

    def _ambiguous_rejected(self, keys, start, end, hit_count):
        """An ambiguous name needs a second match and connector/filler/edge neighbours."""
        phrase = " ".join(keys[start:end])
        if not self._is_ambiguous(phrase):
            return False
        return not (hit_count >= 2 and self._bounded(keys, start, end))

    # ---------- one segment ----------
    def _whole_match(self, seg):
        ids = self.lookup.get(self._normalize(seg), set())
        if len(ids) == 1:
            return Candidate(seg, next(iter(ids)))
        return None

    def _scan(self, keys):
        """Longest-first left-to-right scan: ("hit", start, end, id) or ("word", i, i+1, None)."""
        items, index = [], 0
        while index < len(keys):
            match = self._find_match(keys, index)
            if match:
                items.append(("hit", index, match[0], match[1]))
                index = match[0]
            else:
                items.append(("word", index, index + 1, None))
                index += 1
        return items

    @staticmethod
    def _takes_version(elems, key):
        return bool(elems) and elems[-1].kind == "hit" and elems[-1].version is None \
            and bool(VERSION_RE.match(key))

    def _build_elements(self, keys, items):
        """Accept or reject each hit, attach versions. Returns (elements, accepted_hits)."""
        hit_count = sum(1 for kind, *_ in items if kind == "hit")
        elems, accepted = [], 0
        for kind, start, end, skill_id in items:
            if kind == "hit":
                if self._ambiguous_rejected(keys, start, end, hit_count):
                    elems.extend(_Element("word", key=key) for key in keys[start:end])
                    continue
                elems.append(_Element("hit", text=self._join(keys[start:end]), skill_id=skill_id))
                accepted += 1
            elif self._takes_version(elems, keys[start]):
                version = self._format_version(keys[start])
                elems[-1].version = version
                elems[-1].text = f"{elems[-1].text} {version}"
            else:
                elems.append(_Element("word", key=keys[start]))
        return elems, accepted

    def _unmatched_candidates(self, keys):
        """No skill matched: pass the text on unless it is only filler, connectors or numbers."""
        skip = self.connectors | self.filler_words
        meaningful = [k for k in keys if k and k.lower() not in skip and not NUMERIC_RE.match(k)]
        return [Candidate(self._join(keys), None)] if meaningful else []

    def _split_runs(self, elems):
        """Connector words separate runs of elements."""
        runs = [[]]
        for elem in elems:
            if elem.kind == "word" and elem.key.lower() in self.connectors:
                runs.append([])
            else:
                runs[-1].append(elem)
        return runs

    def _extract_segment(self, segment, label_only=False):
        seg = segment.strip()
        if not seg:
            return []
        whole = self._whole_match(seg)
        if whole:
            return [whole]

        words = seg.split()
        keys = [self._clean(w) for w in words]
        if len(words) > self.max_segment_words:
            return [] if label_only else [Candidate(self._join(keys), None)]

        elems, accepted = self._build_elements(keys, self._scan(keys))
        if accepted == 0:
            return [] if label_only else self._unmatched_candidates(keys)

        out = []
        for run in self._split_runs(elems):
            out.extend(self._run_candidates(run, label_only))
        return out

    def _run_candidates(self, run, label_only):
        hits = [e for e in run if e.kind == "hit"]
        if label_only:
            return [Candidate(h.text, h.skill_id, h.version) for h in hits]

        lefts = [e for e in run if e.kind == "word" and e.key and not NUMERIC_RE.match(e.key)
                 and e.key.lower() not in self.proficiency_words]
        meaningful = {id(e) for e in lefts if e.key.lower() not in self.generic_words}

        if not hits:
            toks = [e.key for e in lefts if id(e) in meaningful]
            return [Candidate(" ".join(toks), None)] if toks else []

        if len(hits) == 1:
            hit = hits[0]
            if not meaningful:
                return [Candidate(hit.text, hit.skill_id, hit.version)]
            keep = {id(e) for e in lefts}
            parts = [e.text if e.kind == "hit" else e.key for e in run
                     if e.kind == "hit" or id(e) in keep]
            return [Candidate(" ".join(parts), None)]       # compound phrase stays whole

        out, buf = [], []

        def flush():
            if buf:
                out.append(Candidate(" ".join(buf), None))
                buf.clear()

        for elem in run:
            if elem.kind == "hit":
                flush()
                out.append(Candidate(elem.text, elem.skill_id, elem.version))
            elif id(elem) in meaningful:
                buf.append(elem.key)
        flush()
        return out

    # ---------- whole input ----------
    @staticmethod
    def _top_level_pieces(text):
        """Split on , ; | newline, but not inside parentheses."""
        pieces, buf, depth = [], [], 0
        for char in text:
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            if char in DELIMS and depth == 0:
                pieces.append("".join(buf))
                buf = []
            else:
                buf.append(char)
        pieces.append("".join(buf))
        return pieces

    def _segments(self, text):
        """Yield (segment, label_only, inner_info) in source order."""
        # Treat ampersands between numeric versions as version-list separators,
        # not as connectors between separate skills (e.g. "ASP.NET Core 3.0 & 6.0").
        text = re.sub(r"(?<=\d)\s*&\s*(?=v?\d)", "/", text)

        # A parenthesized list made entirely of versions belongs to the preceding skill.
        # Convert separators to "/" temporarily so top-level comma splitting cannot break it.
        text = PAREN_VERSION_RE.sub(
            lambda match: " " + VERSION_SEPARATOR_RE.sub("/", match.group(1)) + " ",
            text,
        )

        pieces = self._top_level_pieces(text)

        # Keep bare comma-separated version continuations together, including when
        # the final version is followed by another skill: "React 16, 17, 18 and SQL".
        merged = []
        for piece in pieces:
            current = piece.strip()
            previous_has_version = bool(
                merged
                and re.search(
                    rf"(?:^|\s){VERSION_TOKEN}(?:/{VERSION_TOKEN})*$",
                    merged[-1].strip(),
                    re.IGNORECASE,
                )
            )
            leading_version = re.match(
                rf"^({VERSION_TOKEN})(?=\s|$)(.*)$",
                current,
                re.IGNORECASE,
            )

            if previous_has_version and leading_version:
                merged[-1] = merged[-1].rstrip() + "/" + leading_version.group(1)
                remainder = leading_version.group(2).strip()
                remainder = re.sub(
                    r"^(?:(?:and|with)\s+)",
                    "",
                    remainder,
                    flags=re.IGNORECASE,
                ).strip()
                if remainder:
                    merged.append(remainder)
            else:
                merged.append(piece)

        for piece in merged:
            outer = PAREN_GROUP_RE.sub(" ", piece)
            groups = [(outer, None)]
            for group in PAREN_GROUP_RE.findall(piece):
                items = [x for x in re.split(r"[,;|]", group) if x.strip()]
                groups.extend((item, (outer, len(items))) for item in items)
            for group, info in groups:
                parts = group.split(":")
                for label in parts[:-1]:
                    yield label, True, None
                yield parts[-1], False, info

    @staticmethod
    def _is_short_token(token):
        tok = token.strip()
        return " " not in tok and tok.isalnum() and len(tok) <= 5

    def _is_acronym_of(self, token, phrase):
        tok = token.strip().lower()
        if " " in tok or not tok.isalnum() or len(tok) > 6:
            return False
        words = [self._clean(w) for w in phrase.split() if self._clean(w)]
        full = "".join(w[0] for w in words).lower()
        core = "".join(w[0] for w in words if w.lower() not in self.connectors).lower()
        return tok in {full, core}

    def _is_abbreviation(self, cand, info):
        """True for "(acr)", "(qp)", "(cw1)" that follow the phrase they abbreviate."""
        if not info or cand.skill_id is not None:
            return False
        outer, n_items = info
        return self._is_acronym_of(cand.text, outer) or (
            n_items == 1 and self._is_short_token(cand.text))

    def _dedupe_key(self, cand):
        if cand.skill_id is not None:
            return ("id", cand.skill_id, (cand.version or "").lower())
        return ("text", self._normalize(cand.text))

    def extract_detailed(self, text):
        """Candidates with their skill ID and version, in source order, without duplicates."""
        if not isinstance(text, str) or not text.strip():
            return []
        results, seen = [], set()
        for seg, label_only, info in self._segments(text):
            for cand in self._extract_segment(seg, label_only):
                key = self._dedupe_key(cand)
                if self._is_abbreviation(cand, info) or key in seen:
                    continue
                seen.add(key)
                results.append(cand)
        if not results:                                   # never drop input
            results.append(Candidate(text.strip(), None))
        return results

    def extract(self, text):
        """List of candidate strings for the existing normalizer, in source order."""
        return [c.text for c in self.extract_detailed(text)]
