# Inventory Culinary Assistance

[![CI/CD](https://github.com/duybeobn1/Inventory_Culinary_Assistance/actions/workflows/ci.yml/badge.svg)](https://github.com/duybeobn1/Inventory_Culinary_Assistance/actions/workflows/ci.yml)

> **AI-powered culinary platform** blending Traditional Chinese Medicine (TCM) philosophy with modern AI — computer vision, knowledge graphs, large language models, and real-time cooking assistance.

---

## The Problem

Home cooks and professional chefs lack a single intelligent system that:

- **Tracks inventory** without manual entry (fridge scanning, receipt OCR)
- **Suggests recipes** from what's actually available
- **Considers TCM principles** (Yin-Yang, Five Elements) for dietary balance
- **Adapts to seasons, weather, and region** for optimal ingredient sourcing
- **Provides smart substitutions** — both molecular (chemistry) and philosophical (TCM)
- **Prevents food waste** with expiry tracking and timely alerts
- **Guides cooking in real time** with camera-based step verification

## The Solution

A **full-stack AI platform** where the user flow is:

```
📸 Scan Fridge → ✅ Confirm Inventory → 🧠 AI Chef Suggests Recipes → 🎥 Cook with Live Camera Assistance
```

Each step leverages a different AI capability:

| Step | AI / Engine | Endpoint |
|---|---|---|
| Fridge Scan | GLM-4.6V (vision) | `POST /api/scan_fridge` |
| Receipt OCR | GLM-4.6V (vision) | `POST /api/receipt/parse` |
| Recipe Suggestion | Neo4j Graph-RAG + GLM-4.7-Flash | `POST /api/chef/suggest` |
| TCM Menu Generator | Ollama Qwen3:14b + GLM-4.7-Flash formatting | `POST /api/chef/generate-menu` |
| Molecular Substitution | Neo4j chemical compounds + GLM-4.7-Flash RAG | `GET /api/substitute/molecular/{ingredient}` |
| Philosophical Substitution | Supabase TCM ontology | `GET /api/substitute/philosophical/{ingredient}` |
| Environmental Context | Open-Meteo API → TCM dietary advice | `GET /api/context/environment` |
| Live Cooking OCR | GLM-4.6V (vision) via camera | WebSocket `/ws/cook/{sessionId}` |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Vite + React)                 │
│   InventoryScanner → RecipeDashboard → CookSession   │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP + WebSocket
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend (port 8000)              │
│  ┌──────┐ ┌───────┐ ┌───────┐ ┌──────┐ ┌────────┐  │
│  │ Auth │ │ Chef  │ │Fridge │ │Receip│ │ Cook   │  │
│  │Router│ │Router │ │Router │ │Router│ │Router  │  │
│  └──┬───┘ └───┬───┘ └───┬───┘ └──┬───┘ └───┬────┘  │
│     │         │         │        │         │        │
│  ┌──▼─────────▼─────────▼────────▼─────────▼──────┐ │
│  │              Services Layer                     │ │
│  │  ingredient_service │ auth_service │ cook_service│ │
│  └───────────────────────┬─────────────────────────┘ │
│                          │                           │
│  ┌───────────────────────▼─────────────────────────┐ │
│  │            DB Layer (db/)                        │ │
│  │  supabase.py │ neo4j.py │ ai.py                 │ │
│  └──┬──────────────┬────────────┬──────────────────┘ │
└─────┼──────────────┼────────────┼────────────────────┘
      │              │            │
┌─────▼──────┐ ┌────▼────┐ ┌────▼──────────────┐
│  Supabase   │ │ Neo4j   │ │  AI Services      │
│ (PostgreSQL)│ │ Graph   │ │ GLM │ Ollama      │
│  + Auth     │ │  DB     │ │ Z.ai SDK │ Qwen   │
└────────────┘ └─────────┘ └───────────────────┘
```

### Project Structure

```
.
├── frontend/                         # Vite + React SPA (port 5173)
│   ├── src/
│   │   ├── App.jsx                   # Root component with routes
│   │   ├── main.jsx                  # Entry point
│   │   ├── index.css                 # Global styles
│   │   ├── api.js                    # HTTP + WebSocket client
│   │   ├── i18n.js                   # i18n config (en/fr/vi)
│   │   ├── components/
│   │   │   └── Navbar.jsx            # Top navigation bar
│   │   ├── contexts/
│   │   │   └── ThemeContext.jsx       # Light/dark theme
│   │   └── pages/
│   │       ├── LoginPage.jsx
│   │       ├── InventoryPage.jsx
│   │       ├── InventoryScanner.jsx
│   │       ├── ReceiptUpload.jsx
│   │       ├── RecipeDashboard.jsx   # AI chef recipe suggestions
│   │       ├── SavedRecipesPage.jsx
│   │       ├── CookDashboard.jsx     # /cook landing (resume sessions)
│   │       └── CookSession.jsx       # Live camera cooking assistant
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/                          # FastAPI core service (port 8000)
│   ├── config.py                     # pydantic-settings
│   ├── dependencies.py               # FastAPI DI (JWT auth)
│   ├── logging_config.py
│   ├── middleware.py
│   ├── main.py
│   ├── db/
│   │   ├── supabase.py               # Supabase client
│   │   ├── neo4j.py                  # Neo4j graph driver
│   │   └── ai.py                     # Z.ai GLM client + Ollama
│   ├── services/
│   │   ├── ingredient_service.py     # TCM ingredient logic
│   │   ├── auth_service.py           # Profile & recipe management
│   │   └── cook_service.py           # Session, steps, OCR
│   ├── schemas/
│   │   └── cook.py                   # Cook Pydantic models
│   ├── routers/
│   │   ├── auth.py
│   │   ├── chef.py
│   │   ├── context.py
│   │   ├── fridge.py
│   │   ├── receipts.py
│   │   ├── substitutions.py
│   │   └── cook.py                   # REST + WebSocket endpoints
│   ├── kafka_client.py
│   ├── kafka_worker.py
│   ├── expiry_worker.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── test_main.py                  # 16 tests
├── chef-ai-service/                  # Local Llama-3-8B inference
├── fine-tuning-models/               # LLM LoRA fine-tuning
├── region_ingredient_source_extract/  # Global terroir knowledge base
├── k8s_local_archive/                # Kubernetes manifests
├── docker-compose.yml                # Kafka services
├── init.sql                          # Full database schema
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
| **react-i18next** | Internationalization (en/fr/vi) |
| **React Markdown** | Markdown rendering |
| **Phosphor Icons** | Icon library |
| **Motion** | Animations |
| **CSS Variables** | Theming (light/dark mode) |

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.11** | Runtime |
| **FastAPI** | Web framework (REST + WebSocket) |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Data validation |
| **OpenCV (headless)** | Camera motion detection |
| **Supabase** | PostgreSQL + Auth |
| **Neo4j** | Knowledge graph |
| **Apache Kafka** | Event streaming |

### AI / ML
| Model | Provider | Use |
|---|---|---|
| **GLM-4.6V** | Z.ai (via `zai-sdk`) | Vision: fridge scan, receipt OCR, cooking OCR |
| **GLM-4.7-Flash** | Z.ai (via `zai-sdk`) | Text: recipe generation, substitutions, step extraction |
| **Qwen3:14b** | Ollama (local) | TCM menu reasoning |
| **Llama-3-8B + LoRA** | Hugging Face | TCM ingredient philosophy |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for Kafka)
- Supabase account (free tier)
- Z.ai API key (from https://z.ai or https://open.bigmodel.cn)
- Neo4j AuraDB or local instance
- [Ollama](https://ollama.com) (for local TCM menu generation)

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
SUPABASE_SERVICE_ROLE=your_service_role_key
ZAI_API_KEY=your_zai_api_key
NEO4J_URI=your_neo4j_uri
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Install Ollama & Download Models
[Ollama](https://ollama.com) runs local AI models for TCM menu generation:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the TCM reasoning model
ollama pull qwen3:14b

# (Optional) Pull a vision model for local OCR
ollama pull qwen2-vl:7b

# Verify models are running
ollama list
```

### 4. Run Database Migrations
Execute `init.sql` in your Supabase SQL editor to create all tables, including `cooking_sessions` and `recipe_steps`.

### 5. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 6. Run the Backend
```bash
uvicorn main:app --reload --port 8000
```

### 7. Install & Run Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 8. (Optional) Start Kafka
```bash
docker compose up -d
```

---

## Live Cooking Assistant

The platform includes a real-time cooking assistant with camera-based OCR:

1. **Generate a recipe** on the Chef page, then click **"Start Cooking"**
2. The camera activates — tap to scan or use auto-capture (motion detection every ~15s)
3. **Step-contextual OCR**: checks if you're performing the current step correctly
4. **Freeform mode**: "What is this?" button to identify any ingredient/tool
5. **Step timer + progress bar**: tracks elapsed time per step
6. **WebSocket**: real-time communication for OCR results and step advancement

### Cook API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/cook/session` | Create a new cooking session |
| GET | `/api/cook/sessions` | List active sessions |
| GET | `/api/cook/session/{id}` | Get session state |
| POST | `/api/cook/session/{id}/step` | Advance to next step |
| POST | `/api/cook/session/{id}/pause` | Pause session |
| POST | `/api/cook/session/{id}/resume` | Resume session |
| POST | `/api/cook/session/{id}/abandon` | Abandon session |
| POST | `/api/cook/session/{id}/ocr` | Step-contextual OCR |
| POST | `/api/cook/session/{id}/ocr-freeform` | Freeform OCR |
| WS | `/ws/cook/{sessionId}` | Real-time WebSocket |

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
| POST | `/api/auth/recipes` | Yes | Save a recipe |
| PUT | `/api/auth/recipes/{id}` | Yes | Update saved recipe |
| DELETE | `/api/auth/recipes/{id}` | Yes | Delete saved recipe |

### Fridge & Inventory
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/scan_fridge` | No | Vision scan → ingredient list |
| POST | `/api/inventory/confirm_scan` | Yes | Save verified scan |
| POST | `/api/fridge/manual_add` | Yes | Manually add ingredient |

### Receipts
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/receipt/parse` | Yes | OCR receipt → sync inventory |

### Chef AI
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/chef/analyze-ingredient` | No | TCM philosophy for an ingredient |
| POST | `/api/chef/suggest` | No | Recipe from inventory + Neo4j |
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

### Live Cooking
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/cook/session` | Yes | Create session |
| GET | `/api/cook/sessions` | Yes | List active sessions |
| GET | `/api/cook/session/{id}` | Yes | Get session state |
| POST | `/api/cook/session/{id}/step` | Yes | Advance step |
| POST | `/api/cook/session/{id}/pause` | Yes | Pause session |
| POST | `/api/cook/session/{id}/resume` | Yes | Resume |
| POST | `/api/cook/session/{id}/abandon` | Yes | Abandon |
| POST | `/api/cook/session/{id}/ocr` | Yes | Step OCR |
| POST | `/api/cook/session/{id}/ocr-freeform` | Yes | Freeform OCR |
| WS | `/ws/cook/{sessionId}` | No | WebSocket |

### Health
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Root status |
| GET | `/health` | No | Health check |
| GET | `/health/db` | No | Database connectivity |

---

## Testing

```bash
cd backend
python -m pytest test_main.py -v
```

20 tests covering:
- API health endpoints
- Season determination (both hemispheres)
- TCM weather balance logic
- AI JSON cleaning (with edge cases)
- Fridge capacity mapping
- OCR accuracy validation
- Mass estimation error thresholds
- Authentication flows (signup, signin, profile)

---

## Database Schema

### PostgreSQL (Supabase)
```
profiles           user_id, display_name, preferences
ingredients        name, thermal_property, five_element, tastes
inventory          user_id, ingredient_id, current_quantity, expiry_date
receipts           user_id, vendor, date, total_amount
receipt_line       receipt_id, ingredient_id, quantity, price
notifications      user_id, message, is_read
user_recipes       user_id, recipe_name, recipe_data, is_favorite
cooking_sessions   user_id, recipe_id, recipe_name, total_steps, current_step, status
recipe_steps       recipe_id, step_number, instruction, duration_seconds, ingredients_used, tools_needed
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
- `ZAI_API_KEY`

---

## Switching AI Models

### Using Z.ai (GLM) — Default
The platform uses `zai-sdk` (Z.ai's unified Python SDK) for vision and text:
```python
from zai import ZaiClient, ZhipuAiClient

# Overseas endpoint
client = ZaiClient(api_key="your-key")

# Chinese mainland endpoint
client = ZhipuAiClient(api_key="your-key")
```

### Using Ollama (Local, Free)
For fully local AI, install Ollama and point `model` arguments to local models:
```python
# In db/ai.py — call_ollama()
response = await call_ollama(prompt, model="qwen2-vl:7b")
```

Update `process_ocr_frame` in `cook_service.py` to use `call_ollama` instead of `glm_client` for a free, private alternative.

---

## Fine-Tuned Model

The project includes a pipeline for fine-tuning **Llama-3-8B** with LoRA on TCM culinary philosophy:

- **Base model**: `unsloth/llama-3-8b-Instruct-bnb-4bit`
- **Adapter**: [`duybeobn1/ICA`](https://huggingface.co/duybeobn1/ICA) on Hugging Face Hub
- **Training data**: 1,121 validated JSONL examples
- **Training**: 3 epochs, AdamW 8-bit, r=16 LoRA

```bash
cd fine-tuning-models
python fine_tuning_ggcolab.py   # Run in Google Colab with GPU
python save_model.py            # Push to Hugging Face
```

---

## License

MIT
