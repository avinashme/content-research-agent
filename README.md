# Content Research & Outline Agent

An AI agent that helps with content research and outline generation. Give it a topic or product description, and it will:

1. Decide whether the topic needs a web search or can be answered from general knowledge
2. Search the web and fetch relevant sources
3. Synthesize information across multiple sources
4. Generate a structured content outline (headings, subheadings, bullet points)
5. Add citations linking each point back to its source

Built for content creators, students, and anyone writing essays, articles, or reports who wants a research-backed starting outline instead of a blank page.

## Tech stack
- **Streamlit** – web interface
- **Groq (Llama 3.3 70B)** – decision logic, synthesis, outline generation, citations
- **Tavily** – web search
- **Trafilatura** – clean text extraction from web pages

## How it works
- If the topic is time-sensitive or requires current data (e.g. "Latest AI trends 2026"), the agent searches the web, reads top sources, and builds an outline with citations.
- If the topic is general knowledge (e.g. "Explain photosynthesis"), the agent skips search and generates the outline directly.

## Setup
1. Clone this repo and install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Get free API keys from [Groq](https://console.groq.com) and [Tavily](https://tavily.com)
3. Add them as environment variables or in `.streamlit/secrets.toml`:
   ```
   GROQ_API_KEY = "your_key_here"
   TAVILY_API_KEY = "your_key_here"
   ```
4. Run the app:
   ```
   streamlit run app.py
   ```

## Deployment
Deployed on Streamlit Community Cloud — add your API keys via the app's Secrets settings.
