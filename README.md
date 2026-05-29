# 🥘 Inventory Culinary Assistance

[![CI/CD](https://github.com/duybeobn1/Inventory_Culinary_Assistance/actions/workflows/ci.yml/badge.svg)](https://github.com/duybeobn1/Inventory_Culinary_Assistance/actions/workflows/ci.yml)

> **AI-powered culinary platform** blending Traditional Chinese Medicine (TCM) philosophy with modern AI — computer vision, knowledge graphs, and large language models.

---

## The Problem

Home cooks and professional chefs lack a single intelligent system that:

- **Tracks inventory** without manual entry (fridge scanning, receipt OCR)
- **Suggests recipes** from what's actually available
- **Considers TCM principles** (Yin-Yang, Five Elements) for dietary balance
- **Adapts to seasons, weather, and region** for optimal ingredient sourcing
- **Provides smart substitutions** — both molecular (chemistry) and philosophical (TCM)
- **Prevents food waste** with expiry tracking and timely alerts

## The Solution

A **full-stack AI platform** where the user flow is:

```
📸 Scan Fridge → ✅ Confirm Inventory → 🧠 AI Chef Suggests Recipes → 🍳 Cook & Track
```

Each step leverages a different AI capability:

| Step | AI / Engine | Endpoint |
|---|---|---|
| Fridge Scan | Gemini Vision (volumetric analysis) | `POST /api/scan_fridge` |
| Receipt OCR | Gemini Vision (deskew, denoise, CLAHE) | `POST /api/receipt/parse` |
| Recipe Suggestion | Neo4j Graph-RAG + Gemini | `POST /api/chef/suggest` |
| TCM Menu Generator | Ollama Qwen3:14b + Gemini formatting | `POST /api/chef/generate-menu` |
| Molecular Substitution | Neo4j chemical compounds + Gemini RAG | `GET /api/substitute/molecular/{ingredient}` |
| Philosophical Substitution | Supabase TCM ontology | `GET /api/substitute/philosophical/{ingredient}` |
| Environmental Context | Open-Meteo API → TCM dietary advice | `GET /api/context/environment` |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Vite + React)                 │
│         InventoryScanner → RecipeDashboard           │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────┐
│              FastAPI Backend (port 8000)              │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │  Auth   │ │  Chef    │ │  Fridge  │ │  Receipt│  │
│  │ Router  │ │  Router  │ │  Router  │ │  Router │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬────┘  │
│       │           │            │            │       │
│  ┌────▼───────────▼────────────▼────────────▼────┐  │
│  │              Services Layer                    │  │
│  │  ingredient_service  │  auth_service           │  │
│  └───────────────────────┬───────────────────────┘  │
│                          │                          │
│  ┌───────────────────────▼───────────────────────┐  │
│  │            DB Layer (db/)                      │  │
│  │  supabase.py │ neo4j.py │ ai.py               │  │
│  └──┬──────────────┬────────────┬────────────────┘  │
└─────┼──────────────┼────────────┼────────────────────┘
      │              │            │
┌─────▼──────┐ ┌────▼────┐ ┌────▼──────────────┐
│  Supabase   │ │ Neo4j   │ │  AI Services      │
│ (PostgreSQL)│ │ Graph   │ │ Gemini │ Ollama   │
│  + Auth     │ │  DB     │ │ Llama-3 │ GLM-4   │
└────────────┘ └─────────┘ └───────────────────┘

┌─────────────────────────────────────────────────────┐
│              Infrastructure                          │
│  Kafka ←→ Kafka Worker ←→ Expiry Worker             │
│  Docker │ Kubernetes │ GitHub Actions CI/CD          │
│  Chef AI Service (Llama-3-8B, port 8001)            │
└─────────────────────────────────────────────────────┘
```

### Project Structure

```
.
├── frontend/                         # Vite + React SPA (port 5173)
│   ├── src/
│   │   ├── App.jsx                   # Root component with routes
│   │   ├── main.jsx                  # Entry point (BrowserRouter, ThemeProvider)
│   │   ├── index.css                 # Global styles + CSS variable theming
│   │   ├── api.js                    # HTTP client (axios)
│   │   ├── i18n.js                   # i18n config (en/vi)
│   │   ├── components/
│   │   │   └── Navbar.jsx            # Top navigation bar
│   │   ├── contexts/
│   │   │   └── ThemeContext.jsx       # Light/dark theme provider
│   │   └── pages/
│   │       ├── LoginPage.jsx         # Auth (sign in / sign up)
│   │       ├── InventoryPage.jsx     # View / edit / delete inventory
│   │       ├── InventoryScanner.jsx  # Fridge scan + manual add
│   │       ├── ReceiptUpload.jsx     # Receipt OCR
│   │       ├── RecipeDashboard.jsx   # AI chef recipe suggestions
│   │       └── SavedRecipesPage.jsx  # Saved recipe viewer
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── backend/                          # FastAPI core service (port 8000)
│   ├── config.py                     # Centralized settings (pydantic-settings)
│   ├── dependencies.py               # FastAPI dependency injection
│   ├── logging_config.py             # Structured logging
│   ├── middleware.py                  # Global error handler + request logger
│   ├── main.py                       # App entry point
│   ├── schema.py                     # Pydantic models
│   ├── db/                           # Database clients
│   │   ├── supabase.py               # Supabase (PostgreSQL + Auth)
│   │   ├── neo4j.py                  # Neo4j graph driver
│   │   └── ai.py                     # Gemini / Ollama / Chef AI helpers
│   ├── services/                     # Business logic
│   │   ├── ingredient_service.py     # TCM ingredient creation
│   │   └── auth_service.py           # Profile & recipe management
│   ├── routers/                      # API endpoints
│   │   ├── auth.py                   # /api/auth/*
│   │   ├── chef.py                   # /api/chef/*
│   │   ├── context.py                # /api/context/*
│   │   ├── fridge.py                 # /api/scan_fridge, /api/inventory/*
│   │   ├── receipts.py               # /api/receipt/*
│   │   └── substitutions.py          # /api/substitute/*
│   ├── kafka_client.py               # Kafka producer
│   ├── kafka_worker.py               # Kafka consumer (inventory updates)
│   ├── expiry_worker.py              # Scheduled expiry notifications
│   ├── Dockerfile
│   ├── requirements.txt
│   └── test_main.py                  # 16 tests
├── chef-ai-service/                  # Local Llama-3-8B inference (port 8001)
│   └── main.py                       # FastAPI + LoRA adapter inference
├── fine-tuning-models/               # LLM training pipeline
│   ├── fine_tuning_ggcolab.py        # Unsloth LoRA fine-tuning
│   ├── massive_culinary_dataset.jsonl # 1,122 training examples
│   ├── core_philosophy.txt           # Five Elements & Yin-Yang mappings
│   └── save_model.py                 # Push to Hugging Face Hub
├── region_ingredient_source_extract/ # Global terroir knowledge base
│   ├── extract_database.py           # GLM-4-Flash data generation
│   ├── global_terroir_hierarchical.json  # 905KB JSON
│   └── migrate_terroir.py            # JSON → Neo4j migration
├── k8s_local_archive/                # Kubernetes manifests
│   ├── backend.yaml
│   ├── postgres.yaml
│   ├── vision.yaml
│   └── ocr.yaml
├── docker-compose.yml                # Kafka service
├── init.sql                          # Database schema
└── .github/workflows/ci.yml          # CI/CD pipeline
```

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **Vite** | Build tool |
| **React Router** | Client-side routing |
| **react-i18next** | Internationalization (en/vi) |
| **React Markdown** | Markdown rendering |
| **Phosphor Icons** | Icon library |
| **Geist Variable** | Font |
| **CSS Variables** | Theming (light/dark mode) |

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.11** | Runtime |
| **FastAPI** | Web framework |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Data validation |
| **httpx** | Async HTTP client |
| **OpenCV (headless)** | Image processing |
| **Supabase** | PostgreSQL + Auth |
| **Neo4j** | Knowledge graph |
| **Apache Kafka** | Event streaming |
| **Docker** | Containerization |

### AI / ML
| Model | Provider | Use |
|---|---|---|
| **Gemini 2.5 Flash** | Google | Vision, formatting, recipe compilation |
| **Qwen3:14b** | Ollama (local) | TCM menu reasoning |
| **Llama-3-8B + LoRA** | Hugging Face | TCM ingredient philosophy |
| **GLM-4-Flash** | ZhipuAI | Terroir data generation |

### DevOps
| Tool | Use |
|---|---|
| **GitHub Actions** | CI/CD (tests + Docker build) |
| **Kubernetes** | Production deployment (manifests) |
| **MLflow** | Model versioning (planned) |

---

## Database Schema

### PostgreSQL (Supabase)
```
profiles         user_id, display_name, preferences
ingredients      name, thermal_property, five_element, tastes
inventory        user_id, ingredient_id, current_quantity, expiry_date
receipts         user_id, vendor, date, total_amount
receipt_line     receipt_id, ingredient_id, quantity, price
notifications    user_id, message, is_read
user_recipes     user_id, recipe_name, recipe_data, is_favorite
```

### Neo4j Graph
```
(Ingredient)-[:HAS_COMPOUND]->(Compound)
(Ingredient)-[:IS_SUBSTITUTE_FOR {score}]->(Ingredient)
(Dish)-[:HAS_INGREDIENT]->(Ingredient)
(Country)-[:HAS_REGION]->(Region)-[:IN_SEASON]->(Season)
(Season)-[:PRODUCES]->(Variety)-[:IS_A]->(Ingredient)
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | No | Register with email + password |
| POST | `/api/auth/signin` | No | Login, returns JWT |
| GET | `/api/auth/me` | Yes | Current user profile |
| PUT | `/api/auth/profile` | Yes | Update profile |
| GET | `/api/auth/recipes` | Yes | List saved recipes |

### Fridge & Inventory
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/scan_fridge` | No | Vision scan → ingredient list |
| POST | `/api/inventory/confirm_scan` | Yes | Save verified scan to inventory |
| POST | `/api/fridge/manual_add` | Yes | Manually add ingredient |

### Receipts
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/receipt/parse` | Yes | OCR receipt → sync inventory |

### Chef AI
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/chef/analyze-ingredient` | No | TCM philosophy for an ingredient |
| POST | `/api/chef/suggest` | No | Recipe from inventory + Neo4j graph |
| POST | `/api/chef/generate-menu` | No | 3-course TCM-balanced menu |
| POST | `/api/chef/cook` | No | Log cooking event → Kafka |

### Substitutions
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/substitute/molecular/{name}` | No | Chemical compound substitutes |
| GET | `/api/substitute/philosophical/{name}` | No | TCM-matching substitutes |

### Context
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/context/environment` | No | Weather → TCM dietary advice |

### Health
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Root status |
| GET | `/health` | No | Health check |
| GET | `/health/db` | No | Database connectivity |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for Kafka)
- Supabase account (free tier)
- Gemini API key
- Neo4j AuraDB or local instance

### 1. Clone & Configure
```bash
git clone https://github.com/duybeobn1/Inventory_Culinary_Assistance.git
cd Inventory_Culinary_Assistance/backend
cp .env.example .env   # Fill in your API keys
```

### 2. Set Up Environment Variables
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GEMINI_API_KEY=your_gemini_key
NEO4J_URI=your_neo4j_uri
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Run Database Migrations
Execute `init.sql` in your Supabase SQL editor to create all tables.

### 4. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 6. Install & Run Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 7. (Optional) Start Kafka
```bash
docker compose up -d
```

---

## Testing

```bash
cd backend
python -m pytest test_main.py -v
```

16 tests covering:
- API health endpoints
- Season determination (both hemispheres)
- TCM weather balance logic
- AI JSON cleaning (with edge cases)
- Fridge capacity mapping
- OCR accuracy validation
- Mass estimation error thresholds
- Authentication flows (signup, signin, profile)

---

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`):
1. Checks out code
2. Sets up Python 3.11
3. Installs dependencies
4. Runs unit and accuracy tests
5. Builds Docker image

Secrets required in GitHub:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GEMINI_API_KEY`

---

## Fine-Tuned Model

The project includes a complete pipeline for fine-tuning **Llama-3-8B** with LoRA on TCM culinary philosophy:

- **Base model**: `unsloth/llama-3-8b-Instruct-bnb-4bit`
- **Adapter**: [`duybeobn1/ICA`](https://huggingface.co/duybeobn1/ICA) on Hugging Face Hub
- **Training data**: 1,121 validated JSONL examples from TCM/macrobiotics texts
- **Training**: 3 epochs, AdamW 8-bit, r=16 LoRA

```bash
cd fine-tuning-models
python fine_tuning_ggcolab.py   # Run in Google Colab with GPU
python save_model.py            # Push to Hugging Face
```

The fine-tuning corpus includes:
- *Hoàng Đế Nội Kinh* (Yellow Emperor's Inner Canon)
- *Thực Dưỡng Ohsawa* (Macrobiotics)
- Custom-generated TCM ingredient analyses

---

## Kubernetes Deployment

Production-ready manifests in `k8s_local_archive/`:

```bash
kubectl apply -f k8s_local_archive/postgres.yaml
kubectl apply -f k8s_local_archive/backend.yaml
kubectl apply -f k8s_local_archive/vision.yaml
kubectl apply -f k8s_local_archive/ocr.yaml
```

---

## Roadmap

### ✅ Completed
- Backend architecture (modular FastAPI + middleware + logging)
- Neo4j knowledge graph (ingredients, compounds, dishes, terroir)
- Vision AI fridge scanning + receipt OCR
- TCM recipe suggestion and menu generation
- Molecular and philosophical ingredient substitution
- Supabase authentication (JWT, user-scoped data)
- Environmental context → TCM dietary advice
- Kafka event-driven inventory updates
- Expiry notification scheduler
- CI/CD pipeline
- Fine-tuned Llama-3-8B LoRA adapter
- Global terroir database (8 countries, 905KB JSON → Neo4j)

### 🔄 In Progress
- Native ingredient unit conversion & scaling
- Cooking state detection (doneness, browning) via edge AI

### 🔮 Planned (Epic 4: Real-Time Cooking Assistant)
- State-detection CNNs (doneness, browning, caramelization)
- Edge service with TensorRT on NVIDIA Jetson (~30 FPS)
- Multi-station DAG scheduler with visual alerts
- MLOps pipeline (MLflow, health checks, sub-150ms latency)
- Graceful fallback to timer-based alerts

---

## License

MIT
