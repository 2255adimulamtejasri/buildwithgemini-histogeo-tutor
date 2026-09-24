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

import io
import json
import time
import urllib.parse
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from google import genai
from google.cloud import storage
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from app.a2ui_utils import a2ui_callback
from app.firestore_utils import add_study_topic, get_study_topic, list_study_topics

BUCKET_NAME = "histogeo-tutor-media-d87f671e"
PROJECT_ID = "qwiklabs-gcp-01-d87f671eabf0"

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="Histogeo Tutor, an AI learning assistant specializing in History and Geography for students.",
    workflow_description="Analyze student questions, fetch grounded facts with tools, track study progress in Firestore and Memory, generate visual illustrations or data charts, and return concise, structured UI cards.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms. "
        "When explaining a historical topic or geographical place, use generate_topic_illustration "
        "to generate an image illustration, or generate_topic_chart to generate a data chart/timeline. "
        "You may include one Image component in the card using the exact public https URL "
        "returned by generate_topic_illustration or generate_topic_chart (for example {\"Image\": {\"url\": {\"literalString\": \"https://storage.googleapis.com/...\"}}}). "
        "Never point an Image at a bare filename, an artifact name, or a non-http(s) path. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
        "Ground your historical and geographical facts using the lookup_wikipedia_summary tool. "
        "Manage the student's study_topics records in Firestore using tools: add_study_topic, get_study_topic, list_study_topics. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)



async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to store session facts in Vertex AI Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


def lookup_wikipedia_summary(topic: str) -> str:
    """Fetches real historical or geographical facts from Wikipedia's summary REST API to ground answers.

    Args:
        topic: Name of historical event, empire, figure, or geographic region (e.g. 'Maurya Empire', 'Indus River').

    Returns:
        Factual extract from Wikipedia used for grounding the agent's explanation.
    """
    topic_encoded = urllib.parse.quote(topic.strip().replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic_encoded}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "HistogeoTutor/1.0 (student-learning-assistant)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            title = data.get("title", topic)
            extract = data.get("extract")
            if extract:
                return f"Wikipedia Factual Grounding for '{title}':\n{extract}"
            return f"No summary extract available for '{topic}'."
    except Exception as e:
        return f"Could not fetch Wikipedia summary for '{topic}': {e}"


def search_historical_event(topic: str) -> str:
    """Searches historical records and timelines for an event or era.

    Args:
        topic: Name of historical event, empire, ruler, or battle.

    Returns:
        Structured historical context and key milestones for student revision.
    """
    return (
        f"Historical Record for '{topic}': Key dates, cause, major rulers/figures, "
        f"and lasting impact on world or regional history."
    )


def get_geographic_features(region: str) -> str:
    """Retrieves physical geography details for a place or region.

    Args:
        region: City, region, mountain range, or river valley.

    Returns:
        Overview of terrain, river systems, elevation, and climate characteristics.
    """
    return (
        f"Geographic Overview for '{region}': Terrain features, major rivers, "
        f"elevation, mountain ranges, and climate zones."
    )


async def generate_topic_illustration(
    topic: str,
    topic_type: str,
    tool_context: ToolContext,
) -> str:
    """Generates an illustrative image for a historical event/era or geographic region.

    For historical topics, generates an illustrative scene of the event/era.
    For geography topics, generates a realistic landscape illustration showing the region's hills, river systems, and terrain.

    Args:
        topic: Name of historical event, empire, or geographical region (e.g. 'Maurya Empire', 'Indus River Valley').
        topic_type: Either 'history' or 'geography'.
        tool_context: ADK ToolContext used to save the image artifact.

    Returns:
        Public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the generated image in Cloud Storage.
    """
    topic_clean = "".join(c if c.isalnum() else "_" for c in topic.lower()).strip("_")
    filename = f"{topic_type}_{topic_clean}_{int(time.time())}.jpg"

    if topic_type.lower() == "geography":
        prompt = (
            f"A realistic landscape illustration of {topic}, vividly showing that region's "
            f"hills, mountain ranges, river systems, physical terrain, and climate features."
        )
    else:
        prompt = (
            f"An illustrative historical scene of {topic}, depicting the architecture, "
            f"cultural atmosphere, key historical figures, and era details."
        )

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    part = response.candidates[0].content.parts[0]
    img_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/jpeg"

    # 1. Save artifact in ADK tool_context (Playground Artifacts panel)
    await tool_context.save_artifact(
        filename=filename,
        artifact=types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
    )

    # 2. Upload image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(img_bytes, content_type=mime_type)

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"


async def generate_topic_chart(
    topic: str,
    chart_type: str,
    title: str,
    labels: list[str],
    values: list[float] = None,
    x_label: str = "",
    y_label: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Generates data visualizations (timelines, bar comparison charts, or line charts) using matplotlib.

    Args:
        topic: Subject name (e.g. 'Maurya Empire Timeline', 'Major Rivers Length').
        chart_type: Chart style: 'timeline', 'bar', or 'line'.
        title: Title string for the chart.
        labels: List of label strings for timeline milestones or comparison items.
        values: Optional list of numeric values corresponding to each label (e.g., years or lengths).
        x_label: Optional X-axis label.
        y_label: Optional Y-axis label.
        tool_context: ADK ToolContext to save the chart artifact.

    Returns:
        Public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the chart in Cloud Storage.
    """
    topic_clean = "".join(c if c.isalnum() else "_" for c in topic.lower()).strip("_")
    filename = f"chart_{topic_clean}_{int(time.time())}.png"

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    
    chart_type_lower = chart_type.lower()
    if chart_type_lower == "timeline":
        y_pos = [0] * len(labels)
        ax.scatter(range(len(labels)), y_pos, color="#1a73e8", s=100, zorder=3)
        ax.plot(range(len(labels)), y_pos, color="#4285f4", linewidth=2.5, zorder=2)
        
        for i, txt in enumerate(labels):
            val_str = f" ({values[i]})" if values and i < len(values) else ""
            offset = 0.25 if i % 2 == 0 else -0.35
            ax.annotate(
                f"{txt}{val_str}",
                (i, 0),
                xytext=(i, offset),
                ha="center",
                fontsize=8,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f0fe", ec="#1a73e8", lw=1),
                arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1)
            )
        ax.set_ylim(-1, 1)
        ax.axis("off")

    elif chart_type_lower == "line" and values:
        x_indices = range(len(labels))
        ax.plot(x_indices, values[:len(labels)], marker="o", color="#1a73e8", linewidth=2.5, markersize=7)
        ax.set_xticks(list(x_indices))
        ax.set_xticklabels(labels, rotation=25 if len(labels) > 4 else 0, ha="right" if len(labels) > 4 else "center")
        if x_label: ax.set_xlabel(x_label, fontweight="bold")
        if y_label: ax.set_ylabel(y_label, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)

    else:  # Default to bar chart
        num_vals = values if (values and len(values) == len(labels)) else [1] * len(labels)
        colors = ["#1a73e8", "#34a853", "#fbbc04", "#ea4335", "#8ab4f8", "#a8dab5"]
        bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
        bars = ax.bar(labels, num_vals, color=bar_colors, width=0.5, edgecolor="#202124", linewidth=0.8)
        
        if values:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:g}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25 if len(labels) > 4 else 0, ha="right" if len(labels) > 4 else "center")
        if x_label: ax.set_xlabel(x_label, fontweight="bold")
        if y_label: ax.set_ylabel(y_label, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.5)

    ax.set_title(title or f"{topic} Visualization", fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    img_bytes = buf.getvalue()

    # 1. Save artifact if tool_context available
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            await tool_context.save_artifact(
                filename=filename,
                artifact=types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            )
        except Exception:
            pass

    # 2. Upload image bytes to public GCS bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(img_bytes, content_type="image/png")

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        lookup_wikipedia_summary,
        search_historical_event,
        get_geographic_features,
        generate_topic_illustration,
        generate_topic_chart,
        add_study_topic,
        get_study_topic,
        list_study_topics,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
