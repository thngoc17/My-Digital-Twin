# Building my Digital Twin

---

## 1. Project Overview

This project is an AI system designed for **cloning personal conversational styles and persona integration** (Specialized for Vietnamese).

It consists of two main tasks:

1. **Persona Fine-Tuning** → Fine-tuning a Qwen language model (Qwen3-4B-Instruct) using LoRA to adopt specific communication styles based on the conversation category (e.g., `friends`, `elders`, `polite`).
2. **Retrieval-Augmented Generation (RAG)** → Contextualizing interactions using a vector database for historically accurate, personal data-driven responses.

The pipeline is optimized to work efficiently on consumer hardware utilizing **Unsloth** for fast 4-bit quantization training and inference.

---

## 2. Project Structure

```
root/
├── my_data/
│   ├── facebook_chat
│   └── knowledge_db
│       ├── profile.json (for building personal profile)
│       └── train_data.jsonl (for ChatML conversational training data)
├── src/
│   ├── api.py
│   ├── build_db.py
│   └── process_data.py
├── My Clone (Kaggle Notebook)
├── My Clone API (Kaggle Notebook for Inference & Server deployment)
└── README.md
```

---

## 3. Requirements

* Python **3.10+** - **GPU** recommended (CUDA / cuDNN).

Install dependencies:

```bash
pip install requirements.txt
```

---

## 4. Dataset Preparation

To accurately clone your persona, the pipeline relies on your real conversational history and personal profile data.

### 4.1. Exporting Chat Data

1. Go to your Facebook Settings and navigate to **Download Your Information**.
2. Request a download of your messages, making sure to select **JSON** as the format.
3. Extract the downloaded files and place the main folder into `my_data/facebook_chat/`.
4. If you have multiple data exports, append an index to the folder names to avoid conflicts (e.g., `your_facebook_activity_1`, `your_facebook_activity_2`).

Your directory should look like this:
```text
my_data/
└── facebook_chat/
    ├── your_facebook_activity_1/
    ├── your_facebook_activity_2/
    └── ...
```

### 4.2. Configuring Your Profile

Write your personal information into a `profile.json` file in the root directory. This data will be ingested by the vector database to ground the RAG pipeline with your factual background.

Example `profile.json`:

``` json
[
  {
    "id": "profile_001",
    "category": "gioi_thieu_ban_than",
    "content": "Tôi tên là Lê Thái Ngọc.",
    "metadata": {
      "source": "core_profile",
      "keywords": ["Lê Thái Ngọc", "tên", "họ tên"]
    }
  }
]
```

### 4.3. Processing & Building the Database

Once your raw data and profile are in place, run the preprocessing and database generation scripts. This will parse the JSON chat logs, format them for training, and build the vector database for RAG retrieval.

```bash
python process_data.py
python build_db.py
```
---

## 5. Training

Training the AI persona clone on Kaggle is highly recommended to efficiently leverage cloud GPU resources and easy library management.

### 5.1 Kaggle Notebook

You can access the complete fine-tuning pipeline using the following Kaggle notebook:
[AI Persona Clone - Training Notebook](https://www.google.com/search?q=https://www.kaggle.com/code/thngoc/my-clone)

**Hardware Setup:** Ensure your Kaggle session is configured to use the **T4x2** (Dual Tesla T4) accelerator for optimal training speed and memory management during the LoRA fine-tuning process.

### 5.2 Persona Customization

Before running the training cells, you must update the prompt templates within the notebook. Change the system prompts and conversational formatting to accurately reflect your own personality, communication style, and intended category tags (e.g., `friends`, `elders`, `polite`). This ensures the resulting model captures your authentic voice.

---

## 6. Inference & API Deployment

The inference pipeline is designed to be highly flexible and cost-effective. It uses a split architecture: hosting the language model in the cloud for free, while handling context retrieval (RAG) and bot integration locally.

### 6.1 Hosting the LLM via Kaggle (Free Tier)

Because the fine-tuned model is exported to the **GGUF** format during the training phase, the Qwen 3 4B model is highly optimized and does not require a GPU for inference. You can run it completely free using Kaggle's standard CPU sessions.

1. Open the inference and API notebook: [AI Persona Clone - Inference & API](https://www.kaggle.com/code/lnhingtribcthang/my-clone-api).
2. Load the GGUF output generated from your training notebook.
3. Run the notebook cells. It will load the model and expose it as a web service using **ngrok**.
4. Copy the public ngrok API URL provided in the output.

### 6.2 Local RAG & Telegram Bot Integration

With the heavy lifting of the LLM hosted on Kaggle, your local machine will handle the Vector Database searches (RAG) and interface with your messaging platform.

1. Ensure your local vector database is built (completed in Step 4).
2. Configure your local environment (or `.env` file) with the generated ngrok URL and your Telegram Bot token.
3. Start the local API server:

```bash
python source/api.py
```

`source/api.py` acts as the main orchestrator: it receives messages from the Telegram bot, retrieves the relevant historical context from your local database, sends the RAG-augmented prompt to the Kaggle ngrok endpoint, and delivers the personalized response back to the user.

---

## 7. To-do Works

* **Docker**: Adding the feature for the project to run on Docker for multi-platform training.
* **Training**: Doing more experiments to make better models on both conversational accuracy (tuning LoRA rank/alpha) and RAG retrieval tasks.

---


## 8. License

This project is released under the [MIT License](https://www.google.com/search?q=LICENSE).

---