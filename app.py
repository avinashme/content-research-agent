import os
import streamlit as st
from groq import Groq
from tavily import TavilyClient
import trafilatura

st.set_page_config(page_title="Content Research & Outline Agent", layout="centered")

st.title("Content Research & Outline Agent")
st.write("Enter a topic or product description below to get started.")

# --- API Clients (read from environment variables / Streamlit secrets) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY", "")

if not GROQ_API_KEY or not TAVILY_API_KEY:
    st.error("Missing API keys. Set GROQ_API_KEY and TAVILY_API_KEY as environment variables or in Streamlit secrets.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


# --- Step 2: Decision logic ---
def needs_search(topic_text: str) -> str:
    prompt = f"""Topic: "{topic_text}"

Decide if answering this topic well requires a web search
(e.g. it involves recent events, current data, specific products,
prices, statistics, or anything that may have changed recently).

Reply with ONLY one word: "yes" or "no". No explanation."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().lower()


# --- Step 3: Web search tool ---
def web_search(query: str, max_results: int = 5):
    response = tavily_client.search(query=query, max_results=max_results)
    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", "")
        })
    return results


# --- Step 4: Source fetcher/parser ---
def fetch_clean_text(url: str, max_chars: int = 2000) -> str:
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return "[Could not fetch content]"
    text = trafilatura.extract(downloaded)
    if text is None:
        return "[Could not extract text]"
    return text[:max_chars]


# --- Step 5: Multi-source synthesizer ---
def synthesize_sources(topic_text: str, sources: list) -> str:
    combined_text = ""
    for i, src in enumerate(sources, start=1):
        combined_text += f"\n--- Source {i}: {src['title']} ({src['url']}) ---\n"
        combined_text += src['text'][:1500]
        combined_text += "\n"

    prompt = f"""Topic: "{topic_text}"

Below are excerpts from multiple sources. Cross-reference and combine
the key information into a single, well-organized synthesized summary.
Mention agreements/overlaps across sources where relevant. Keep it concise
(150-250 words).

Sources:
{combined_text}

Synthesized summary:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# --- Step 6: Outline generator ---
def generate_outline(topic_text: str, synthesized_text: str) -> str:
    prompt = f"""Topic: "{topic_text}"

Based on the synthesized information below, create a structured content
outline using markdown formatting:
- Use "## " for main sections
- Use "### " for subsections
- Use "- " for bullet points under each section/subsection

The outline should be logical, well-organized, and cover the key points.

Synthesized information:
{synthesized_text}

Outline (markdown format):"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# --- Step 7: Citation mapper ---
def add_citations(topic_text: str, outline_md: str, sources: list) -> str:
    source_list_text = "\n".join(
        f"[{i+1}] {s['title']} - {s['url']}" for i, s in enumerate(sources)
    )

    prompt = f"""Topic: "{topic_text}"

Here is a content outline (markdown):
{outline_md}

Here is a list of available sources:
{source_list_text}

Task: For each bullet point in the outline, append the most relevant
source link in markdown format like this: ([source title](url)).
If a point doesn't clearly map to a specific source, you can leave it
without a citation. Keep the original outline structure (##, ###, -)
intact, only add citations at the end of bullet lines.

Return the full outline with citations added (markdown format):"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# --- Step 8: Orchestration (agent loop) ---
def run_pipeline(topic_text: str, status=None):
    result = {
        "topic": topic_text,
        "decision": None,
        "search_results": [],
        "synthesized_summary": None,
        "outline_md": None,
        "cited_outline": None,
    }

    if status:
        status.update(label="Deciding if web search is needed...")
    decision = needs_search(topic_text)
    result["decision"] = decision

    if decision.startswith("yes"):
        if status:
            status.update(label="Searching the web...")
        search_results = web_search(topic_text)
        result["search_results"] = search_results

        if status:
            status.update(label="Fetching and reading sources...")
        sources_for_synthesis = []
        for r in search_results:
            text = fetch_clean_text(r['url'])
            sources_for_synthesis.append({
                "title": r['title'],
                "url": r['url'],
                "text": text
            })

        if status:
            status.update(label="Synthesizing information from sources...")
        synthesized_summary = synthesize_sources(topic_text, sources_for_synthesis)
        result["synthesized_summary"] = synthesized_summary

        if status:
            status.update(label="Generating outline...")
        outline_md = generate_outline(topic_text, synthesized_summary)
        result["outline_md"] = outline_md

        if status:
            status.update(label="Adding citations...")
        cited_outline = add_citations(topic_text, outline_md, search_results)
        result["cited_outline"] = cited_outline
    else:
        if status:
            status.update(label="Generating outline...")
        outline_md = generate_outline(topic_text, f"General knowledge topic: {topic_text}")
        result["outline_md"] = outline_md
        result["cited_outline"] = outline_md

    return result


# --- UI ---
topic = st.text_input("Topic / Product Description", placeholder="e.g. Benefits of intermittent fasting")

if st.button("Generate"):
    if topic.strip() == "":
        st.warning("Please enter a topic before clicking Generate.")
    else:
        with st.status("Starting agent pipeline...", expanded=True) as status:
            result = run_pipeline(topic, status=status)
            status.update(label="Done!", state="complete", expanded=False)

        st.divider()

        # Search decision badge
        if result["decision"].startswith("yes"):
            st.caption("🔍 Web search was used for this topic")
        else:
            st.caption("🧠 Answered from general knowledge (no search needed)")

        # Main output: the outline
        st.header(result["topic"])
        st.markdown(result["cited_outline"])

        # Optional details in expanders (keeps main view clean)
        if result["search_results"]:
            with st.expander("📄 View synthesized summary"):
                st.write(result["synthesized_summary"])

            with st.expander(f"🔗 Sources ({len(result['search_results'])})"):
                for i, r in enumerate(result["search_results"], start=1):
                    st.markdown(f"**[{i}] {r['title']}**")
                    st.markdown(f"[{r['url']}]({r['url']})")
                    st.caption(r['snippet'][:200] + "...")
                    st.write("")

        # Footnote-style source list at the bottom
        if result["search_results"]:
            st.divider()
            st.write("#### References")
            for i, r in enumerate(result["search_results"], start=1):
                st.markdown(f"{i}. [{r['title']}]({r['url']})")
