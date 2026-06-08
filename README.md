# 🏦 FinRAG — AI-Powered Wealth Advisor RAG Pipeline
> A production-grade Retrieval-Augmented Generation (RAG) system on AWS for financial document intelligence — SEBI circulars, insurance policies, and mutual fund catalogues — powering a Claude-based wealth advisor.

---

## 📌 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Data Pipeline — Stage by Stage](#data-pipeline--stage-by-stage)
- [AWS Services Used](#aws-services-used)
- [VPC & Network Design](#vpc--network-design)
- [Folder Structure](#folder-structure)
- [Build Order](#build-order)
- [Local Setup](#local-setup)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Testing the Pipeline](#testing-the-pipeline)
- [Mac Finder → S3 Integration](#mac-finder--s3-integration)
- [Roadmap](#roadmap)

---

## Project Overview

FinRAG is a fully automated document ingestion and retrieval pipeline built on AWS. It accepts financial documents (PDFs, JSONs), processes them through a type-aware parsing system, chunks and embeds them using AWS Bedrock, and stores them in a managed vector knowledge base — ready for semantic search by a Claude-powered wealth advisor.

**Core Capabilities:**
- Automatic pipeline trigger on S3 document upload
- Document-type-aware parsing (SEBI / Insurance / Catalogue)
- Semantic chunking with metadata tagging
- Vector embeddings via AWS Bedrock Titan Embeddings v2
- Managed vector search via Bedrock Knowledge Base
- Full audit trail in S3 chunk store
- All services deployed inside a private VPC via AWS CDK (Python)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS VPC (Private Network)                       │
│                                                                           │
│   ┌─────────────┐     ┌──────────────┐     ┌─────────────────────────┐  │
│   │  S3 Input   │────▶│  Doc Type    │────▶│     Parser Lambdas      │  │
│   │   Bucket    │     │    Router    │     │  ┌─────────────────────┐ │  │
│   │  (trigger)  │     │   (Lambda)   │     │  │   SEBI Parser       │ │  │
│   └─────────────┘     └──────────────┘     │  │  (PyMuPDF + regex)  │ │  │
│                                             │  ├─────────────────────┤ │  │
│                                             │  │  Insurance Parser   │ │  │
│                                             │  │ (Unstructured + tbl)│ │  │
│                                             │  ├─────────────────────┤ │  │
│                                             │  │  Catalogue Parser   │ │  │
│                                             │  │  (JSON / struct PDF)│ │  │
│                                             └──┴─────────────────────┘ │  │
│                                                          │               │  │
│                                                          ▼               │  │
│                                             ┌─────────────────────────┐ │  │
│                                             │   Semantic Chunker      │ │  │
│                                             │ (RecursiveCharSplitter) │ │  │
│                                             └────────────┬────────────┘ │  │
│                                                          │               │  │
│                                                          ▼               │  │
│                                             ┌─────────────────────────┐ │  │
│                                             │    Metadata Tagger      │ │  │
│                                             │ doc_type│source│date    │ │  │
│                                             │ entity │ chunk_id       │ │  │
│                                             └────────────┬────────────┘ │  │
│                                                          │               │  │
│                          ┌───────────────────────────────┘               │  │
│                          │                                                │  │
│              ┌───────────▼──────────┐      ┌──────────────────────────┐ │  │
│              │  Bedrock Embeddings  │      │     S3 Chunk Store       │ │  │
│              │  Titan Embeddings v2 │─────▶│  (text + metadata +      │ │  │
│              │  (1536-dim vectors)  │      │   vectors backup)        │ │  │
│              └───────────┬──────────┘      └──────────────────────────┘ │  │
│                          │                                                │  │
│                          ▼                                                │  │
│              ┌───────────────────────┐                                   │  │
│              │  Bedrock Knowledge    │                                   │  │
│              │       Base            │                                   │  │
│              │  (Vector DB — Upsert) │                                   │  │
│              └───────────────────────┘                                   │  │
│                                                                           │  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────┐
                     │   Claude Wealth Advisor   │
                     │  (Query → Embed → Search  │
                     │   → Retrieve → Answer)    │
                     └──────────────────────────┘
```

---

## Data Pipeline — Stage by Stage

### Stage 1 — S3 Upload Event *(Trigger)*
- Documents are uploaded to the **S3 Input Bucket** (manually, via CLI, or via Mac Finder using S3 Mountpoint)
- S3 fires an **event notification** automatically on every new object
- This event invokes the **Doc Type Router Lambda** — no manual intervention needed

---

### Stage 2 — Doc Type Router *(Traffic Cop)*
- Inspects the incoming file's name, prefix, and metadata
- Determines document category: `SEBI` | `Insurance` | `Catalogue`
- Routes the file to the correct parser Lambda
- Acts as the single entry point for all document types

---

### Stage 3 — Parsers *(Readers)*

| Parser | Method | Best For |
|---|---|---|
| **SEBI Parser** | `PyMuPDF` + `regex` | Text-heavy regulatory PDFs, circular IDs, dated headings |
| **Insurance Parser** | `Unstructured` + table extract | Complex layouts, premium tables, footnotes, coverage grids |
| **Catalogue Parser** | JSON / structured PDF parsing | Mutual fund data, NAV, risk ratings, structured fields |

Each parser outputs clean, structured text ready for chunking.

---

### Stage 4 — Semantic Chunker *(Cutter)*
- Uses `RecursiveCharacterTextSplitter` from LangChain
- Splits documents at natural boundaries (paragraphs → sentences → words)
- Maintains semantic coherence — no idea is split mid-thought
- Configurable `chunk_size` and `chunk_overlap` per document type

---

### Stage 5 — Metadata Tagger *(Label Maker)*
Each chunk is tagged with:

```json
{
  "doc_type": "SEBI | Insurance | Catalogue",
  "source": "s3://bucket/path/to/original.pdf",
  "date": "2024-03-15",
  "entity": "SEBI | LIC | HDFC | SBI",
  "chunk_id": "uuid-v4",
  "page_number": 3,
  "pipeline_version": "1.0.0"
}
```

Metadata enables **pre-filtering** before vector search — e.g., "only search SEBI docs from 2024" — dramatically improving accuracy and speed.

---

### Stage 6 — Bedrock Embeddings *(Translator)*
- AWS Bedrock **Titan Embeddings v2** model converts each chunk into a **1536-dimensional vector**
- Vectors capture semantic meaning mathematically
- Chunks about similar concepts cluster numerically close — enabling meaning-based search
- A backup copy (text + metadata + raw vector) is saved to the **S3 Chunk Store**

---

### Stage 7 — Bedrock KB Upsert *(Index Filing)*
- Each vector is upserted (insert or update) into the **Bedrock Knowledge Base**
- Bedrock KB maintains an optimised HNSW vector index for sub-second similarity search
- On user query: question → embed → vector search → top-K chunks retrieved → sent to Claude

---

### Query Flow (Runtime)

```
User Question
     │
     ▼
Embed question (Titan v2)
     │
     ▼
Vector similarity search in Bedrock KB
     │
     ▼
Top-K relevant chunks retrieved
     │
     ▼
Chunks + Question sent to Claude as context
     │
     ▼
Claude generates grounded, cited answer
```

---

## AWS Services Used

| Service | Purpose |
|---|---|
| **Amazon S3** | Input document storage + chunk backup store |
| **AWS Lambda** | Router, parsers, chunker, tagger, embedder (serverless compute) |
| **Amazon Bedrock** | Titan Embeddings v2 (embedding model) + Knowledge Base (vector DB) |
| **Amazon VPC** | Private network isolating all services |
| **AWS IAM** | Role-based access control between all services |
| **Amazon CloudWatch** | Lambda logs, pipeline monitoring, alerts |
| **AWS CDK (Python)** | Infrastructure as Code — deploys all of the above |

---

## VPC & Network Design

All services run inside a **private VPC** for security and compliance.

```
VPC (CIDR: 10.0.0.0/16)
├── Public Subnets (10.0.1.0/24, 10.0.2.0/24)
│   └── NAT Gateway
├── Private Subnets (10.0.3.0/24, 10.0.4.0/24)
│   ├── Lambda Functions (Router, Parsers, Chunker, Tagger, Embedder)
│   └── VPC Endpoints → S3, Bedrock (private traffic, no internet)
└── Internet Gateway (for NAT only)
```

**VPC Endpoints** ensure Lambda → S3 and Lambda → Bedrock traffic **never leaves AWS's private network**, improving both security and latency.

---

## Folder Structure

```
rag-pipeline/
├── app.py                        # CDK app entry point
├── cdk.json                      # CDK configuration
├── requirements.txt              # Python dependencies
│
├── stacks/
│   ├── vpc_stack.py              # VPC, subnets, NAT, endpoints
│   ├── storage_stack.py          # S3 input bucket + chunk store
│   ├── iam_stack.py              # IAM roles and policies
│   ├── bedrock_stack.py          # Bedrock KB + vector index
│   └── pipeline_stack.py        # All Lambdas + S3 event trigger
│
├── lambdas/
│   ├── router/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── sebi_parser/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── insurance_parser/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── catalogue_parser/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── chunker/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── tagger/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── embedder/
│       ├── handler.py
│       └── requirements.txt
│
└── tests/
    ├── test_sebi_parser.py
    ├── test_insurance_parser.py
    ├── test_chunker.py
    └── test_embedder.py
```

---

## Build Order

Follow this exact sequence. Each phase depends on the previous.

```
Phase 1 — Foundation
  [1] vpc_stack.py          → VPC, subnets, NAT gateway, VPC endpoints
  [2] storage_stack.py      → S3 input bucket + S3 chunk store
  [3] iam_stack.py          → IAM roles for Lambda, Bedrock, S3

Phase 2 — AI Core
  [4] bedrock_stack.py      → Bedrock Knowledge Base + vector index
  [5] Manual test           → Verify Bedrock embeddings via boto3

Phase 3 — Pipeline Lambdas (build + test each individually)
  [6]  Router Lambda
  [7]  SEBI Parser Lambda
  [8]  Insurance Parser Lambda
  [9]  Catalogue Parser Lambda
  [10] Chunker Lambda
  [11] Tagger Lambda
  [12] Embedder + KB Upsert Lambda

Phase 4 — Wiring
  [13] S3 event → Router Lambda trigger
  [14] Lambda → Lambda invocation chain
  [15] VPC endpoints verified

Phase 5 — Validation
  [16] Drop test PDF into S3
  [17] Monitor CloudWatch logs end-to-end
  [18] Query Bedrock KB and verify retrieval
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (required by CDK CLI)
- AWS CLI configured (`aws configure`)
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Bedrock model access enabled in your AWS account (Titan Embeddings v2)

### Install Dependencies

```bash
# Clone the repo
git clone https://github.com/your-org/rag-pipeline.git
cd rag-pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# Install Python dependencies
pip install -r requirements.txt
```

---

## Deployment

```bash
# One-time bootstrap (sets up CDK in your AWS account/region)
cdk bootstrap aws://ACCOUNT_ID/REGION

# Preview what will be created (no AWS changes)
cdk synth

# Deploy Phase 1 first
cdk deploy VpcStack
cdk deploy StorageStack
cdk deploy IamStack

# Deploy Phase 2
cdk deploy BedrockStack

# Deploy Phase 3 + 4
cdk deploy PipelineStack

# Or deploy everything at once (only after individual testing)
cdk deploy --all
```

### Tear Down
```bash
cdk destroy --all    # removes all AWS resources cleanly
```

---

## Environment Variables

Store these in AWS Systems Manager Parameter Store or a `.env` file (never commit to Git):

```env
AWS_ACCOUNT_ID=123456789012
AWS_REGION=ap-south-1
S3_INPUT_BUCKET=finrag-input-docs
S3_CHUNK_STORE_BUCKET=finrag-chunk-store
BEDROCK_KB_ID=your-knowledge-base-id
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## Testing the Pipeline

### 1. Upload a test document
```bash
aws s3 cp tests/sample_sebi_circular.pdf s3://finrag-input-docs/sebi/
```

### 2. Watch Lambda logs in real time
```bash
aws logs tail /aws/lambda/FinRAG-Router --follow
aws logs tail /aws/lambda/FinRAG-SebiParser --follow
aws logs tail /aws/lambda/FinRAG-Embedder --follow
```

### 3. Query the Knowledge Base
```python
import boto3

bedrock = boto3.client("bedrock-agent-runtime", region_name="ap-south-1")

response = bedrock.retrieve(
    knowledgeBaseId="your-kb-id",
    retrievalQuery={"text": "What are SEBI's latest mutual fund regulations?"},
    retrievalConfiguration={
        "vectorSearchConfiguration": {"numberOfResults": 5}
    }
)

for result in response["retrievalResults"]:
    print(result["content"]["text"])
    print(result["score"])
```

---

## Mac Finder → S3 Integration

To make a local folder on your Mac behave as a direct S3 upload trigger:

### Option A — S3 Mountpoint (Recommended)
```bash
# Install
brew install --cask mountpoint-s3

# Mount your S3 input bucket as a local folder
mount-s3 finrag-input-docs ~/Documents/FinRAG-Docs
```
Dropping a file in `~/Documents/FinRAG-Docs` in Finder **directly writes to S3** and fires the pipeline instantly.

### Option B — Watchdog Script
```bash
pip install watchdog boto3
python scripts/folder_watcher.py --folder ~/Documents/FinRAG-Docs --bucket finrag-input-docs
```

---

## Roadmap

- [x] VPC & network design
- [x] S3 buckets (input + chunk store)
- [x] IAM roles
- [x] Bedrock Knowledge Base
- [ ] Doc Type Router Lambda
- [ ] SEBI Parser Lambda
- [ ] Insurance Parser Lambda
- [ ] Catalogue Parser Lambda
- [ ] Semantic Chunker Lambda
- [ ] Metadata Tagger Lambda
- [ ] Embedder + KB Upsert Lambda
- [ ] End-to-end pipeline test
- [ ] Claude Wealth Advisor query interface
- [ ] CloudWatch dashboard & alerting
- [ ] Multi-region support

---

## Contributing

1. Create a feature branch: `git checkout -b feature/sebi-parser`
2. Build and test your Lambda locally before deploying
3. Run `cdk synth` before any PR
4. Never commit `.env` files or AWS credentials

---

*Built with AWS CDK (Python) · AWS Bedrock · Claude by Anthropic*
