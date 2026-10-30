# 📊 AI WhatsApp Intelligence — Analytics & Monitoring Dashboard

This directory contains the standalone web client for the **AI WhatsApp Intelligence Hub**.

## 🚀 Key Capabilities

- **⚡ Real-Time Intelligence Stream**: Subscribes directly to `/api/v1/dashboard/stream` via Server-Sent Events (SSE) for live message ingestion and status badges.
- **🧠 Conversational Vector RAG**: Type natural language questions across WhatsApp group history and receive AI-grounded answers with source message citations.
- **🔍 Semantic Vector Search**: High-dimensional cosine similarity matching against embedded group conversations.
- **📝 Autonomous Executive Briefings**: Generate structured executive summaries, key decisions, action items with urgency flags, and open questions across selectable timeframes (24h, 72h, 7d, 30d).
- **📥 One-Click Export**: Instant intelligence export to Markdown (`.md`), CSV (`.csv`), and JSON (`.json`).

## 🛠️ Quick Start

### Option 1: Built-in Zero-Config Dashboard
The FastAPI backend serves this interactive dashboard out-of-the-box at:
```
http://localhost:8000/dashboard
```

### Option 2: Run Standalone with Vite
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.
