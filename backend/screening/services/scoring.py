import math
import re
from functools import lru_cache

from .chunking import chunk_text
from .ollama import embed, embed_many

SKILL_WEIGHT = 0.7
EMBED_WEIGHT = 0.3
# max chars embedded in one call; keeps snippets within the embedding model's
# 512-token context (mxbai-embed-large) so nothing is silently truncated.
EMBED_TEXT_LIMIT = 1500
SEMANTIC_MATCH_THRESHOLD = 0.62
PHRASE_WORD_OVERLAP_THRESHOLD = 0.55

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "shall", "can", "need", "dedicated", "required", "requirements", "qualification",
    "qualifications", "responsibility", "responsibilities", "experience", "years", "year",
    "work", "working", "team", "role", "position", "job", "description", "candidate",
    "candidates", "ability", "strong", "excellent", "good", "plus", "preferred", "including",
    "etc", "our", "your", "you", "we", "they", "their", "this", "that", "these", "those",
    "about", "within", "across", "using", "used", "use", "via", "per", "able", "well",
    "minimum", "preferred", "knowledge", "understanding", "familiarity", "proficiency",
}

SKILL_LEXICON = {
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "nosql", "html",
    "css", "sass", "react", "reactjs", "nextjs", "next.js", "vue", "vuejs", "angular",
    "svelte", "nodejs", "node.js", "express", "django", "flask", "fastapi", "spring",
    "springboot", ".net", "laravel", "rails", "graphql", "rest", "api", "microservices",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "aws", "azure", "gcp",
    "cloud", "devops", "ci/cd", "cicd", "jenkins", "github actions", "gitlab", "linux",
    "unix", "bash", "shell", "powershell", "git", "agile", "scrum", "kanban", "jira",
    "confluence", "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "kafka", "rabbitmq", "spark", "hadoop", "airflow", "dbt", "snowflake", "databricks",
    "tableau", "power bi", "powerbi", "looker", "excel", "pandas", "numpy", "scikit-learn",
    "sklearn", "tensorflow", "pytorch", "keras", "opencv", "nlp", "llm", "rag", "machine learning",
    "deep learning", "data science", "data analysis", "data engineering", "statistics",
    "computer vision", "etl", "bi", "analytics", "figma", "sketch", "ui/ux", "ux", "ui",
    "selenium", "cypress", "jest", "pytest", "unit testing", "integration testing",
    "tdd", "oop", "solid", "design patterns", "system design", "architecture",
    "leadership", "communication", "collaboration", "problem solving", "mentoring",
    "project management", "stakeholder management", "presentation", "english",
    "vietnamese", "mandarin", "japanese", "korean", "spanish", "french", "german",
    "bachelor", "master", "phd", "degree", "certification", "certified",
    "aws certified", "pmp", "cpa", "cfa", "security", "cybersecurity", "oauth",
    "jwt", "authentication", "authorization", "encryption", "blockchain", "web3",
    "mobile", "android", "ios", "flutter", "react native", "xamarin", "unity", "unreal",
    "sap", "salesforce", "hubspot", "crm", "erp", "seo", "sem", "marketing",
    "copywriting", "content writing", "technical writing", "customer service",
    "accounting", "finance", "budgeting", "forecasting", "supply chain", "logistics",
    "hr", "recruiting", "onboarding", "training", "quality assurance", "qa",
    "manual testing", "automation testing", "performance testing", "load testing",
    "support", "troubleshooting", "debugging", "code review", "pair programming",
    "full stack", "fullstack", "frontend", "front-end", "backend", "back-end",
    "software engineering", "software development", "web development", "mobile development",
    "embedded", "firmware", "iot", "robotics", "research", "publication",
}

SKILL_ALIASES: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript", "node", "nodejs", "node.js", "react", "vue", "angular"],
    "typescript": ["ts"],
    "python": ["py", "django", "flask", "fastapi", "pandas", "numpy"],
    "machine learning": ["ml", "ai", "artificial intelligence", "deep learning", "neural network"],
    "data science": ["data scientist", "data analysis", "analytics"],
    "kubernetes": ["k8s", "container orchestration"],
    "amazon web services": ["aws", "ec2", "s3", "lambda"],
    "google cloud platform": ["gcp", "google cloud"],
    "microsoft azure": ["azure"],
    "continuous integration": ["ci/cd", "cicd", "devops pipeline"],
    "postgresql": ["postgres", "psql"],
    "rest": ["restful", "rest api", "web api", "http api"],
    "api": ["apis", "web services", "microservices"],
    "leadership": ["lead", "leading", "managed", "mentored", "supervised"],
    "communication": ["communicate", "presenting", "presentation", "written communication"],
    "problem solving": ["problem-solving", "analytical", "troubleshooting"],
    "agile": ["scrum", "kanban", "sprint"],
    "quality assurance": ["qa", "testing", "test automation"],
}

REQUIREMENT_SECTION_PATTERN = re.compile(
    r"(requirements?|qualifications?|must[\s-]?have(?:s)?|skills?|"
    r"what you(?:'|’)ll bring|what we(?:'|’)re looking for|"
    r"minimum qualifications?|preferred qualifications?)\s*:?\s*",
    re.IGNORECASE,
)

BULLET_PATTERN = re.compile(r"^[\s]*(?:[-*•●▪▸►]|\d+[.)])\s+", re.MULTILINE)


def _normalize_lookup(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _cosine_similarity(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _content_words(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z0-9+#./-]{2,}", _normalize_lookup(text))
        if word not in STOPWORDS and not word.isdigit()
    ]


def _find_lexicon_skills(text: str) -> set[str]:
    lowered = _normalize_lookup(text)
    found: set[str] = set()

    for skill in SKILL_LEXICON:
        pattern = rf"(?<![a-z0-9+#./-]){re.escape(skill)}(?![a-z0-9+#./-])"
        if re.search(pattern, lowered):
            found.add(skill)

    return found


def _extract_bullet_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for line in text.splitlines():
        cleaned = BULLET_PATTERN.sub("", line).strip(" \t-•*")
        if not cleaned:
            continue
        if 4 <= len(cleaned) <= 160:
            phrases.append(cleaned)
    return phrases


def _extract_requirement_block(jd_text: str) -> str:
    match = REQUIREMENT_SECTION_PATTERN.search(jd_text)
    if not match:
        return jd_text

    start = match.end()
    remainder = jd_text[start:]
    next_heading = re.search(r"\n\s*[A-Z][A-Za-z /&-]{2,40}:\s*\n", remainder)
    if next_heading:
        return remainder[: next_heading.start()]
    return remainder


def _is_requirement_covered(requirement: str, existing: list[str]) -> bool:
    requirement_norm = _normalize_lookup(requirement)
    for item in existing:
        item_norm = _normalize_lookup(item)
        if requirement_norm in item_norm or item_norm in requirement_norm:
            return True
    return False


def _extract_jd_requirements(jd_text: str) -> list[str]:
    requirements: list[str] = []
    requirement_text = _extract_requirement_block(jd_text)

    for phrase in _extract_bullet_phrases(requirement_text):
        if not _is_requirement_covered(phrase, requirements):
            requirements.append(phrase)

    if len(requirements) < 3:
        for line in requirement_text.splitlines():
            cleaned = line.strip(" \t-•*")
            if 12 <= len(cleaned) <= 160 and not _is_requirement_covered(cleaned, requirements):
                requirements.append(cleaned)

    for skill in sorted(_find_lexicon_skills(jd_text)):
        if not _is_requirement_covered(skill, requirements):
            requirements.append(skill)

    if len(requirements) < 5:
        for part in re.split(r"[,;/|]", requirement_text):
            cleaned = part.strip()
            if 3 <= len(cleaned) <= 80 and not _is_requirement_covered(cleaned, requirements):
                requirements.append(cleaned)

    return requirements[:40]


def _term_in_text(term: str, text: str) -> bool:
    pattern = rf"(?<![a-z0-9+#./-]){re.escape(term)}(?![a-z0-9+#./-])"
    return re.search(pattern, text) is not None


def _alias_match(requirement: str, resume_lookup: str) -> bool:
    requirement_norm = _normalize_lookup(requirement)

    for canonical, aliases in SKILL_ALIASES.items():
        candidates = [canonical, *aliases]
        if not any(candidate in requirement_norm for candidate in candidates):
            continue
        if any(_term_in_text(candidate, resume_lookup) for candidate in candidates):
            return True

    return False


def _phrase_word_overlap(requirement: str, resume_lookup: str) -> float:
    words = _content_words(requirement)
    if not words:
        return 0.0

    hits = sum(1 for word in words if _term_in_text(word, resume_lookup))
    return hits / len(words)


def _phrase_in_text(requirement: str, resume_lookup: str) -> bool:
    requirement_norm = _normalize_lookup(requirement)
    if requirement_norm in resume_lookup:
        return True

    return _phrase_word_overlap(requirement, resume_lookup) >= PHRASE_WORD_OVERLAP_THRESHOLD


@lru_cache(maxsize=512)
def _cached_embed(text: str) -> tuple[float, ...]:
    return tuple(embed(text))


@lru_cache(maxsize=128)
def _cached_embed_many(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    if not texts:
        return ()
    embeddings = embed_many(list(texts))
    return tuple(tuple(item) for item in embeddings)


def _build_resume_embeddings(
    resume_text: str,
    resume_embeddings: list[list[float]] | None,
) -> list[tuple[float, ...]]:
    if resume_embeddings:
        return [tuple(item) for item in resume_embeddings]

    chunks = chunk_text(resume_text) or [resume_text[:EMBED_TEXT_LIMIT]]
    return [_cached_embed(chunk) for chunk in chunks]


def requirement_match_score(
    resume_text: str,
    jd_text: str,
    resume_embeddings: list[list[float]] | None = None,
) -> dict:
    resume_lookup = _normalize_lookup(resume_text)
    requirements = _extract_jd_requirements(jd_text)
    chunk_embeddings = _build_resume_embeddings(resume_text, resume_embeddings)

    if not requirements:
        return {
            "score": 0.0,
            "matchedSkills": [],
            "missingSkills": [],
            "jdSkillCount": 0,
            "semanticThreshold": SEMANTIC_MATCH_THRESHOLD,
        }

    text_matched: dict[str, bool] = {}
    semantic_candidates: list[str] = []
    for requirement in requirements:
        if _phrase_in_text(requirement, resume_lookup) or _alias_match(requirement, resume_lookup):
            text_matched[requirement] = True
        else:
            semantic_candidates.append(requirement)

    # Embed every requirement that needs the semantic fallback in ONE batched
    # Ollama call, then score them against the resume chunk embeddings.
    semantic_scores: dict[str, float] = {}
    if semantic_candidates and chunk_embeddings:
        snippets = tuple(req[:EMBED_TEXT_LIMIT] for req in semantic_candidates)
        embeddings = _cached_embed_many(snippets)
        for requirement, requirement_embedding in zip(semantic_candidates, embeddings):
            semantic_scores[requirement] = max(
                _cosine_similarity(requirement_embedding, chunk_embedding)
                for chunk_embedding in chunk_embeddings
            )

    matched: list[str] = []
    missing: list[str] = []
    for requirement in requirements:
        if text_matched.get(requirement):
            matched.append(requirement)
        elif semantic_scores.get(requirement, 0.0) >= SEMANTIC_MATCH_THRESHOLD:
            matched.append(requirement)
        else:
            missing.append(requirement)

    score = (len(matched) / len(requirements)) * 100

    return {
        "score": score,
        "matchedSkills": matched,
        "missingSkills": missing,
        "jdSkillCount": len(requirements),
        "semanticThreshold": SEMANTIC_MATCH_THRESHOLD,
    }


def embedding_similarity_score(resume_text: str, jd_text: str) -> float:
    resume_snippet = resume_text[:EMBED_TEXT_LIMIT]
    jd_snippet = jd_text[:EMBED_TEXT_LIMIT]

    resume_embedding = _cached_embed(resume_snippet)
    jd_embedding = _cached_embed(jd_snippet)
    similarity = _cosine_similarity(resume_embedding, jd_embedding)

    return max(0.0, min(1.0, similarity)) * 100


def compute_hybrid_score(
    resume_text: str,
    jd_text: str,
    resume_embeddings: list[list[float]] | None = None,
) -> dict:
    overlap = requirement_match_score(resume_text, jd_text, resume_embeddings)
    skill_score = overlap["score"]
    embed_score = embedding_similarity_score(resume_text, jd_text)

    if overlap["jdSkillCount"] == 0:
        final_score = embed_score
        skill_weight = 0.0
        embed_weight = 1.0
    else:
        final_score = (SKILL_WEIGHT * skill_score) + (EMBED_WEIGHT * embed_score)
        skill_weight = SKILL_WEIGHT
        embed_weight = EMBED_WEIGHT

    return {
        "score": int(round(max(0, min(100, final_score)))),
        "scoreBreakdown": {
            "skillOverlap": int(round(skill_score)),
            "embeddingSimilarity": int(round(embed_score)),
            "skillWeight": skill_weight,
            "embeddingWeight": embed_weight,
            "matchedSkills": overlap["matchedSkills"],
            "missingSkills": overlap["missingSkills"],
            "jdSkillCount": overlap["jdSkillCount"],
            "semanticThreshold": overlap["semanticThreshold"],
        },
    }
