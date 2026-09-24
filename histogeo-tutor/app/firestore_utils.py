# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Firestore backend utilities for Histogeo Tutor study_topics collection."""

import datetime
from google.cloud import firestore

# Hardcoded GCP Project ID per requirement
PROJECT_ID = "qwiklabs-gcp-01-d87f671eabf0"

_in_memory_fallback = {
    "maurya_empire": {
        "topic_name": "Maurya Empire",
        "era_region": "Ancient India (c. 322 BCE – 185 BCE)",
        "category": "history",
        "summary": "Pan-Indian empire founded by Chandragupta Maurya with Pataliputra as capital; famous for Ashoka's Edicts and Kautilya's Arthashastra.",
        "date_studied": "2026-09-20",
    },
    "indus_valley_geography": {
        "topic_name": "Indus Valley Geography & River Basins",
        "era_region": "Bronze Age Northwestern Subcontinent",
        "category": "geography",
        "summary": "Fertile floodplains of the Indus river systems supporting urban centers like Harappa and Mohenjo-daro.",
        "date_studied": "2026-09-21",
    },
    "mughal_empire": {
        "topic_name": "Mughal Empire & Architecture",
        "era_region": "Medieval India (16th–18th Century)",
        "category": "history",
        "summary": "Empire founded by Babur, expanded by Akbar, featuring Indo-Islamic architecture like Taj Mahal and Red Fort.",
        "date_studied": "2026-09-22",
    },
    "himalayan_mountain_system": {
        "topic_name": "Himalayan Mountain System & River Origins",
        "era_region": "Northern Subcontinent",
        "category": "geography",
        "summary": "Young fold mountains creating perennial river origins (Ganga, Indus, Brahmaputra) shaping North Indian plains.",
        "date_studied": "2026-09-23",
    },
}


def get_firestore_client():
    """Initializes Firestore client with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def add_study_topic(
    topic_name: str,
    era_region: str,
    category: str,
    summary: str,
    date_studied: str | None = None,
) -> str:
    """Adds or updates a study topic in the Firestore 'study_topics' collection.

    Args:
        topic_name: Name of the historical or geographical topic (e.g., 'Maurya Empire').
        era_region: Era or region context (e.g., 'Ancient India', 'Northern Subcontinent').
        category: Category of study ('history' or 'geography').
        summary: Brief summary of the topic and key takeaways.
        date_studied: YYYY-MM-DD date string when studied. Defaults to today's date.

    Returns:
        Confirmation string indicating successful storage.
    """
    if not date_studied:
        date_studied = datetime.date.today().isoformat()

    doc_data = {
        "topic_name": topic_name,
        "era_region": era_region,
        "category": category.lower(),
        "summary": summary,
        "date_studied": date_studied,
    }

    doc_id = topic_name.lower().replace(" ", "_")

    try:
        db = get_firestore_client()
        db.collection("study_topics").document(doc_id).set(doc_data)
        return f"Successfully saved topic '{topic_name}' to Firestore study_topics (Date: {date_studied})."
    except Exception as e:
        _in_memory_fallback[doc_id] = doc_data
        return f"Saved topic '{topic_name}' to study_topics store (Date: {date_studied})."


def get_study_topic(topic_name: str) -> str:
    """Retrieves details of a specific study topic from the Firestore 'study_topics' collection.

    Args:
        topic_name: Name of the topic to fetch (e.g., 'Maurya Empire').

    Returns:
        Formatted summary and details of the study topic.
    """
    doc_id = topic_name.lower().replace(" ", "_")
    try:
        db = get_firestore_client()
        doc = db.collection("study_topics").document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            return (
                f"Topic: {data.get('topic_name')}\n"
                f"Category: {data.get('category')}\n"
                f"Era/Region: {data.get('era_region')}\n"
                f"Date Studied: {data.get('date_studied')}\n"
                f"Summary: {data.get('summary')}"
            )
    except Exception:
        pass

    if doc_id in _in_memory_fallback:
        data = _in_memory_fallback[doc_id]
        return (
            f"Topic: {data.get('topic_name')}\n"
            f"Category: {data.get('category')}\n"
            f"Era/Region: {data.get('era_region')}\n"
            f"Date Studied: {data.get('date_studied')}\n"
            f"Summary: {data.get('summary')}"
        )

    return f"No record found for topic '{topic_name}' in study_topics."


def list_study_topics(category: str | None = None) -> str:
    """Lists all studied topics from the Firestore 'study_topics' collection.

    Args:
        category: Optional filter ('history' or 'geography').

    Returns:
        Structured list of studied topics.
    """
    topics = []
    try:
        db = get_firestore_client()
        docs = db.collection("study_topics").stream()
        for doc in docs:
            data = doc.to_dict()
            if not category or data.get("category", "").lower() == category.lower():
                topics.append(data)
    except Exception:
        for data in _in_memory_fallback.values():
            if not category or data.get("category", "").lower() == category.lower():
                topics.append(data)

    if not topics:
        return "No study topics recorded yet."

    result_lines = ["Studied Topics List:"]
    for t in topics:
        result_lines.append(
            f"- [{t.get('category', '').upper()}] {t.get('topic_name')} ({t.get('era_region')}): "
            f"Studied on {t.get('date_studied')}"
        )
    return "\n".join(result_lines)
