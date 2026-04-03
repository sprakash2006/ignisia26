# Knowledge Retrieval System (RAG)

A production-ready RAG (Retrieval-Augmented Generation) system designed for multi-format document analysis with a focus on data integrity, conflict detection, and structured reasoning.

## 🚀 Key Features

- **Multi-Format Ingestion**: Support for Excel (.xlsx), CSV, PDF, Word (.docx), and Text (.txt) files.
- **Excel-Aware Reasoning**: Row-level chunking for spreadsheets to maintain structural context.
- **Data Quality Guardrails**: 
    - Automated detection of **duplicate** and **conflicting** information across documents.
    - Strict anti-hallucination prompts to ensure answers are grounded ONLY in provided context.
- **Structured AI Responses**: Every answer includes:
    - ✅ **Final Answer**: Direct response to the query.
    - ⚠️ **Data Quality Notes**: Report on missing values, conflicts, or duplicates.
    - 🧾 **Source References**: Specific citations (File, Page/Row, Section).
    - 🧠 **Reasoning**: Explanation of how the answer was derived.
- **Vector Database**: Built-on ChromaDB for efficient similarity search.
- **Interactive UI**: Clean Streamlit interface for document management and chat.

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/sprakash2006/ignisia26.git
cd ignisia26
```

### 2. Create and Activate Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.

**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory and add your OpenAI API key:
```env
OPENAI_API_KEY=your_api_key_here
```

### 5. Run the Application
```bash
streamlit run app.py
```

---
*Built for reliable enterprise knowledge retrieval.*
