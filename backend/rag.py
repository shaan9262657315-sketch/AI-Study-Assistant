import os
import re
from typing import List, Optional

import pymupdf
import requests

from dotenv import load_dotenv
from google import genai

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Production = Gemini
# Local development = Ollama
AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "gemini"
).lower().strip()


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# CONFIG
# =========================================================

PDF_FOLDER = "pdfs"

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)

PDF_RELEVANCE_THRESHOLD = 0.08

os.makedirs(
    PDF_FOLDER,
    exist_ok=True
)


# =========================================================
# RAG STORAGE
# =========================================================

documents = []

vectorizer = None

tfidf_matrix = None


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text: str):

    text = text.replace(
        "\x00",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# QUERY NORMALIZATION
# =========================================================

def normalize_query(query: str):

    query = query.lower().strip()

    replacements = {

        "oops": "oop object oriented programming",

        "o.o.p": "oop object oriented programming",

        "o.o.p.s": "oop object oriented programming",

        "object oriented":
            "object oriented programming",

        "object-oriented":
            "object oriented programming",

        "obj oriented":
            "object oriented programming",

        "dbms":
            "database management system",

        "os":
            "operating system",

        "cn":
            "computer networks",

        "dsa":
            "data structures algorithms",

        "ai":
            "artificial intelligence",

        "ml":
            "machine learning",

        "rag":
            "retrieval augmented generation",
    }

    for old, new in replacements.items():

        query = re.sub(
            rf"\b{re.escape(old)}\b",
            new,
            query
        )

    return query


# =========================================================
# TEXT CHUNKING
# =========================================================

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150
):

    text = clean_text(text)

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():

            chunks.append(
                chunk.strip()
            )

        if end >= len(text):

            break

        start = end - overlap

    return chunks


# =========================================================
# PDF EXTRACTION
# =========================================================

def extract_pdf(pdf_path: str):

    doc = pymupdf.open(
        pdf_path
    )

    pages = []

    for page_number, page in enumerate(
        doc,
        start=1
    ):

        text = page.get_text()

        text = clean_text(
            text
        )

        if text:

            pages.append({

                "page": page_number,

                "text": text

            })

    page_count = len(doc)

    doc.close()

    return pages, page_count


# =========================================================
# INDEX PDF
# =========================================================

def index_pdf(
    pdf_path: str,
    document_id: str,
    filename: str
):

    global documents

    pages, page_count = extract_pdf(
        pdf_path
    )

    # Prevent duplicate indexing

    documents = [

        item

        for item in documents

        if item["document_id"] != document_id

    ]

    for page_data in pages:

        chunks = chunk_text(
            page_data["text"]
        )

        for chunk in chunks:

            documents.append({

                "document_id":
                    document_id,

                "filename":
                    filename,

                "page":
                    page_data["page"],

                "text":
                    chunk

            })

    rebuild_index()

    return page_count


# =========================================================
# BUILD TF-IDF INDEX
# =========================================================

def rebuild_index():

    global vectorizer

    global tfidf_matrix

    if not documents:

        vectorizer = None

        tfidf_matrix = None

        return

    texts = [

        item["text"]

        for item in documents

    ]

    vectorizer = TfidfVectorizer(

        lowercase=True,

        stop_words="english",

        ngram_range=(1, 2)

    )

    tfidf_matrix = vectorizer.fit_transform(
        texts
    )


# =========================================================
# REMOVE PDF
# =========================================================

def remove_document(
    document_id: str
):

    global documents

    documents = [

        item

        for item in documents

        if item["document_id"] != document_id

    ]

    rebuild_index()


# =========================================================
# CLEAR INDEX
# =========================================================

def clear_index():

    global documents

    documents = []

    rebuild_index()


# =========================================================
# SEARCH PDF
# =========================================================

def search_documents(
    query: str,
    top_k: int = 5,
    selected_documents: Optional[List[str]] = None
):

    if not documents or vectorizer is None:

        return []

    normalized_query = normalize_query(
        query
    )

    query_vector = vectorizer.transform(
        [normalized_query]
    )

    similarities = cosine_similarity(
        query_vector,
        tfidf_matrix
    )[0]

    results = []

    for index, score in enumerate(
        similarities
    ):

        item = documents[index]

        if (
            selected_documents
            and item["document_id"]
            not in selected_documents
        ):

            continue

        results.append({

            **item,

            "score": float(score)

        })

    results.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    return results[:top_k]


# =========================================================
# GEMINI
# =========================================================

def generate_gemini_answer(
    question: str,
    context: str,
    language: str = "english",
    outside_knowledge: bool = False
):

    if not gemini_client:

        print(
            "Gemini client is not available."
        )

        return None

    if outside_knowledge:

        instruction = """
You are an AI Study Assistant.

Answer using your general knowledge.

Do not pretend the answer came from the PDF.

Do not invent facts.

Keep the answer simple and student-friendly.
"""

    else:

        instruction = """
You are an AI Study Assistant.

Answer the student's question using ONLY
the supplied PDF context.

Do not invent information that is not
supported by the PDF.

Keep the answer simple and student-friendly.
"""

    if language.lower() == "hinglish":

        instruction += """
Answer in simple Hinglish.
Use natural Hindi + English.
Keep technical terms in English.
"""

    elif language.lower() == "hindi":

        instruction += """
Answer in simple Hindi.
Keep standard technical terms in English
when necessary.
"""

    else:

        instruction += """
Answer in clear, simple English.
"""

    prompt = f"""
{instruction}

STUDENT QUESTION:

{question}

PDF CONTEXT:

{context}

First give the direct answer.
Then give a short explanation.
"""

    try:

        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt

        )

        if response.text:

            return response.text.strip()

        return None

    except Exception as e:

        print(
            "Gemini Error:",
            e
        )

        return None


# =========================================================
# OLLAMA
# =========================================================

def generate_ollama_answer(
    question: str,
    context: str,
    language: str = "english",
    outside_knowledge: bool = False
):

    if outside_knowledge:

        instruction = """
You are an AI Study Assistant.

Answer using your general knowledge.

Do not pretend the answer came from the PDF.

Do not invent facts.

Keep the answer simple and student-friendly.
"""

    else:

        instruction = """
You are an AI Study Assistant.

Answer the student's question using ONLY
the supplied PDF context.

Do not invent information that is not
supported by the PDF.

Keep the answer simple and student-friendly.
"""

    if language.lower() == "hinglish":

        instruction += """
Answer in simple Hinglish.
Use natural Hindi + English.
Keep technical terms in English.
"""

    elif language.lower() == "hindi":

        instruction += """
Answer in simple Hindi.
Keep standard technical terms in English
when necessary.
"""

    else:

        instruction += """
Answer in clear, simple English.
"""

    prompt = f"""
{instruction}

STUDENT QUESTION:

{question}

PDF CONTEXT:

{context}

First give the direct answer.
Then give a short explanation.
"""

    try:

        response = requests.post(

            OLLAMA_URL,

            json={

                "model":
                    OLLAMA_MODEL,

                "prompt":
                    prompt,

                "stream":
                    False

            },

            timeout=120

        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response"
        )

        if answer:

            return answer.strip()

        return None

    except Exception as e:

        print(
            "Ollama Error:",
            e
        )

        return None


# =========================================================
# COMMON AI FUNCTION
# =========================================================

def generate_answer(
    question: str,
    context: str,
    language: str = "english",
    outside_knowledge: bool = False
):
    """
    Unified AI provider.

    AI_PROVIDER=ollama
        Ollama is primary.
        Gemini is fallback.

    AI_PROVIDER=gemini
        Gemini is primary.
        Ollama is fallback.
    """

    provider = AI_PROVIDER.lower().strip()

    # =====================================================
    # OLLAMA PRIMARY
    # =====================================================

    if provider == "ollama":

        print("AI Provider: Ollama")

        answer = generate_ollama_answer(
            question=question,
            context=context,
            language=language,
            outside_knowledge=outside_knowledge
        )

        if answer:
            return answer

        # -------------------------------------------------
        # OLLAMA FAILED ? GEMINI FALLBACK
        # -------------------------------------------------

        print("Ollama failed. Trying Gemini fallback...")

        answer = generate_gemini_answer(
            question=question,
            context=context,
            language=language,
            outside_knowledge=outside_knowledge
        )

        if answer:
            return answer

        return None

    # =====================================================
    # GEMINI PRIMARY
    # =====================================================

    if provider == "gemini":

        print("AI Provider: Gemini")

        answer = generate_gemini_answer(
            question=question,
            context=context,
            language=language,
            outside_knowledge=outside_knowledge
        )

        if answer:
            return answer

        # -------------------------------------------------
        # GEMINI FAILED ? OLLAMA FALLBACK
        # -------------------------------------------------

        print("Gemini failed. Trying Ollama fallback...")

        answer = generate_ollama_answer(
            question=question,
            context=context,
            language=language,
            outside_knowledge=outside_knowledge
        )

        if answer:
            return answer

        return None

    # =====================================================
    # INVALID PROVIDER
    # =====================================================

    print(
        f"Unknown AI_PROVIDER '{provider}'. "
        "Using Ollama as fallback."
    )

    return generate_ollama_answer(
        question=question,
        context=context,
        language=language,
        outside_knowledge=outside_knowledge
    )

# =========================================================
# ASK QUESTION
# =========================================================

def ask_question(
    question: str,
    mode: str = "pdf_gemini",
    language: str = "english",
    selected_documents: Optional[List[str]] = None,
    top_k: int = 5
):

    results = search_documents(

        query=question,

        top_k=top_k,

        selected_documents=selected_documents

    )

    # -----------------------------------------------------
    # CHECK PDF RELEVANCE
    # -----------------------------------------------------

    relevant_results = [

        result

        for result in results

        if result["score"]
        >= PDF_RELEVANCE_THRESHOLD

    ]

    # -----------------------------------------------------
    # NO RELEVANT PDF
    # -----------------------------------------------------

    if not relevant_results:

        outside_answer = generate_answer(

            question=question,

            context="",

            language=language,

            outside_knowledge=True

        )

        if outside_answer:

            return {

                "answer":
                    outside_answer,

                "sources":
                    []

            }

        return {

            "answer":
                "AI is currently unavailable.",

            "sources":
                []

        }

    # -----------------------------------------------------
    # BUILD CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for result in relevant_results:

        page = result.get(
            "page",
            "Unknown"
        )

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            continue

        context_parts.append(

            f"[Page {page}]\n{text}"

        )

    context = "\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # GENERATE ANSWER
    # -----------------------------------------------------

    answer = generate_answer(

        question=question,

        context=context,

        language=language,

        outside_knowledge=False

    )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    if not answer:

        answer = (
            "AI is currently unavailable. "
            "Please try again later."
        )

    return {

        "answer":
            answer,

        "sources":
            relevant_results

    }


# =========================================================
# LOAD EXISTING PDFS
# =========================================================

def load_existing_pdfs(
    pdf_records
):

    clear_index()

    for record in pdf_records:

        if os.path.exists(
            record.file_path
        ):

            index_pdf(

                record.file_path,

                record.document_id,

                record.filename

            )


# =========================================================
# PROVIDER INFO
# =========================================================

def get_ai_provider():

    return {

        "provider":
            AI_PROVIDER,

        "gemini_model":
            GEMINI_MODEL,

        "ollama_model":
            OLLAMA_MODEL

    }

