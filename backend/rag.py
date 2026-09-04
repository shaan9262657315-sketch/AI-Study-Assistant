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

# Local  -> ollama
# Production -> gemini
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")


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

OLLAMA_URL = "http://localhost:11434/api/generate"

OLLAMA_MODEL = "llama3.2:3b"

GEMINI_MODEL = "gemini-3.6-flash"

# Agar best similarity isse kam hai,
# to PDF ko relevant nahi maana jayega.

PDF_RELEVANCE_THRESHOLD = 0.08

os.makedirs(
    PDF_FOLDER,
    exist_ok=True
)


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

        "object oriented": "object oriented programming",

        "object-oriented": "object oriented programming",

        "obj oriented": "object oriented programming",

        "dbms": "database management system",

        "os": "operating system",

        "cn": "computer networks",

        "dsa": "data structures algorithms",

        "ai": "artificial intelligence",

        "ml": "machine learning",

        "rag": "retrieval augmented generation",
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

                "document_id": document_id,

                "filename": filename,

                "page": page_data["page"],

                "text": chunk

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

    # Normalize student query

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

        # Selected PDF filter

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

    # -----------------------------------------------------
    # OUTSIDE PDF KNOWLEDGE
    # -----------------------------------------------------

    if outside_knowledge:

        instruction = """
You are an AI Study Assistant.

The uploaded PDF does not contain relevant information
for the student's question.

Answer using your general knowledge.

Give the actual answer.
Do not say only "not found".
Do not pretend the answer came from the PDF.
Do not invent facts.
Keep the explanation simple and student-friendly.
"""

    # -----------------------------------------------------
    # ANSWER FROM PDF
    # -----------------------------------------------------

    else:

        instruction = """
You are an AI Study Assistant.

Answer the student's question using ONLY the supplied
PDF context.

Do not invent information that is not supported by
the PDF.

If the PDF contains a definition, explain it clearly.

If the PDF contains an example, use it when useful.

Keep the answer simple and student-friendly.

First give the direct answer.
Then give a short explanation.
"""

    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

    if language.lower() == "hinglish":

        instruction += """
Answer in simple Hinglish.
Use natural Hindi + English.
Keep technical terms in English.
"""

    elif language.lower() == "hindi":

        instruction += """
Answer in simple Hindi.
Keep standard technical terms in English when necessary.
"""

    else:

        instruction += """
Answer in clear, simple English.
"""

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
{instruction}

STUDENT QUESTION:

{question}

PDF CONTEXT:

{context}

Now answer the student's question.

First give the direct answer.
Then give a short explanation.
"""

    # -----------------------------------------------------
    # GEMINI REQUEST
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # OUTSIDE PDF KNOWLEDGE
    # -----------------------------------------------------

    if outside_knowledge:

        system_instruction = """
You are an AI Study Assistant.

The uploaded PDF does not contain relevant information
for the student's question.

Therefore, answer the question using your general knowledge.

IMPORTANT:
- Give the actual answer.
- Do not say only "not found".
- Do not pretend the answer came from the PDF.
- Never invent facts.
- Never guess technical terms.
- Use standard meanings of technical concepts.
- If the question asks for a full form, give the standard full form.
- Keep the answer simple and student-friendly.
"""

    # -----------------------------------------------------
    # ANSWER FROM PDF
    # -----------------------------------------------------

    else:

        system_instruction = """
You are an AI Study Assistant.

Answer the student's question using ONLY the supplied
PDF context.

IMPORTANT:
- The PDF context is relevant to the student's question.
- Do not ignore the supplied context.
- Do not replace the PDF information with unrelated information.
- Do not invent facts that are not supported by the PDF.
- If the PDF contains a definition, explain that definition clearly.
- If the PDF contains an example, use it when useful.
- Keep the answer simple and student-friendly.
- Answer the actual question, not a different question.
"""

    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

    if language.lower() == "hinglish":

        system_instruction += """
Answer in simple Hinglish.
Use natural Hindi + English.
Keep technical terms in English.
"""

    elif language.lower() == "hindi":

        system_instruction += """
Answer in simple Hindi.
Keep standard technical terms in English when necessary.
"""

    else:

        system_instruction += """
Answer in clear, simple English.
"""

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
{system_instruction}

STUDENT QUESTION:
{question}
"""

    if context:

        prompt += f"""

SUPPLIED PDF CONTEXT:
{context}
"""

    if outside_knowledge:

        prompt += """

The PDF context is not relevant enough for this question.

Now answer the student's question using your general knowledge.

First give the direct answer.
Then give a short explanation.
"""

    else:

        prompt += """

Now answer the student's question using the supplied PDF context.

First give the direct answer.
Then give a short explanation.
"""

    # -----------------------------------------------------
    # OLLAMA REQUEST
    # -----------------------------------------------------

    try:

        response = requests.post(

            OLLAMA_URL,

            json={

                "model": OLLAMA_MODEL,

                "prompt": prompt,

                "stream": False,

                "options": {

                    "temperature": 0.2

                }

            },

            timeout=120

        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response",
            ""
        ).strip()

        if not answer:

            return None

        return answer

    except requests.RequestException as e:

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

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    if AI_PROVIDER.lower() == "gemini":

        return generate_gemini_answer(

            question=question,

            context=context,

            language=language,

            outside_knowledge=outside_knowledge

        )

    # -----------------------------------------------------
    # OLLAMA
    # -----------------------------------------------------

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
    mode: str = "pdf_ollama",
    language: str = "english",
    selected_documents: Optional[List[str]] = None,
    top_k: int = 5
):

    # -----------------------------------------------------
    # SEARCH PDF
    # -----------------------------------------------------

    results = search_documents(

        query=question,

        top_k=top_k,

        selected_documents=selected_documents

    )

    # -----------------------------------------------------
    # NO RESULTS
    # -----------------------------------------------------

    if not results:

        outside_answer = generate_answer(

            question=question,

            context="",

            language=language,

            outside_knowledge=True

        )

        if outside_answer:

            if language.lower() == "hinglish":

                final_answer = (

                    "🌐 Outside PDF Knowledge:\n\n"

                    "Uploaded PDF me is question ka "
                    "relevant answer nahi mila.\n\n"

                    + outside_answer

                )

            elif language.lower() == "hindi":

                final_answer = (

                    "🌐 PDF ke bahar ki jaankari:\n\n"

                    "Uploaded PDF me is question ka "
                    "relevant answer nahi mila.\n\n"

                    + outside_answer

                )

            else:

                final_answer = (

                    "🌐 Outside PDF Knowledge:\n\n"

                    "The uploaded PDF does not contain "
                    "relevant information for this question.\n\n"

                    + outside_answer

                )

            return {

                "answer": final_answer,

                "sources": []

            }

        return {

            "answer": (

                "The answer was not found in the PDF, "
                "and the selected AI provider is unavailable."
            ),

            "sources": []

        }

    # -----------------------------------------------------
    # BEST SCORE
    # -----------------------------------------------------

    best_score = results[0]["score"]

    # -----------------------------------------------------
    # PDF NOT RELEVANT
    # -----------------------------------------------------

    if best_score < PDF_RELEVANCE_THRESHOLD:

        outside_answer = generate_answer(

            question=question,

            context="",

            language=language,

            outside_knowledge=True

        )

        if outside_answer:

            if language.lower() == "hinglish":

                final_answer = (

                    "🌐 Outside PDF Knowledge:\n\n"

                    "Uploaded PDF me is question ka "
                    "relevant answer nahi mila.\n\n"

                    + outside_answer

                )

            elif language.lower() == "hindi":

                final_answer = (

                    "🌐 PDF ke bahar ki jaankari:\n\n"

                    "Uploaded PDF me is question ka "
                    "relevant answer nahi mila.\n\n"

                    + outside_answer

                )

            else:

                final_answer = (

                    "🌐 Outside PDF Knowledge:\n\n"

                    "The uploaded PDF does not contain "
                    "relevant information for this question.\n\n"

                    + outside_answer

                )

            return {

                "answer": final_answer,

                "sources": []

            }

    # -----------------------------------------------------
    # BUILD PDF CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for result in results:

        context_parts.append(

            f"[{result['filename']} - "
            f"Page {result['page']}]\n"
            f"{result['text']}"

        )

    context = "\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # PDF ONLY
    # -----------------------------------------------------

    if mode == "pdf_only":

        answer = (

            "📚 Answer from PDF:\n\n"

            + context

        )

    # -----------------------------------------------------
    # PDF + AI
    # -----------------------------------------------------

    else:

        ai_answer = generate_answer(

            question=question,

            context=context,

            language=language,

            outside_knowledge=False

        )

        if ai_answer:

            answer = (

                "📚 Answer from PDF:\n\n"

                + ai_answer

            )

        else:

            answer = (

                "📚 Relevant information found in PDF:\n\n"

                + context

                + "\n\n"

                "⚠️ AI provider is currently unavailable."

            )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {

        "answer": answer,

        "sources": results

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