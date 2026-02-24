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

* Python **3.10+** - **GPU** recommended (CUDA / cuDNN) for training and faster inference

Install dependencies:

```bash
pip install unsloth peft trl
pip install transformers==4.56.2

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

## 6. Inference (Real Conversation)

Run inference using the fine-tuned LoRA checkpoint:

```bash
python src/inference/run_inference.py \
  --base_model unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit \
  --lora_checkpoint path/to/checkpoint \
  --category friends \
  --input_text "Hôm nay đi đá bóng không?"

```

Example shell script:

```bash
#!/bin/bash
python src/inference/infer_persona.py \
  --lora_checkpoint models/persona_clone_best \
  --user_input "Can you explain this AI project?" \
  --style polite

```

---

## 7. To-do Works

* **Docker**: Adding the feature for the project to run on Docker for multi-platform training.
* **Training**: Doing more experiments to make better models on both conversational accuracy (tuning LoRA rank/alpha) and RAG retrieval tasks.

---


## 8. License

This project is released under the [MIT License](https://www.google.com/search?q=LICENSE).

---