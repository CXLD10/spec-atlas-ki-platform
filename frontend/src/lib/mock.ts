/**
 * Mock data for development and fallback when API is unavailable.
 * Includes both repository and document sources, realistic and diverse.
 */

import { Source, KnowledgeCard } from './types'

export const MOCK_SOURCES: Source[] = [
  // Repos
  {
    id: 'repo-hf-transformers',
    type: 'repo',
    name: 'huggingface/transformers',
    subtitle: 'Hugging Face · State-of-the-art ML library',
    status: 'ready',
    stats: { entities: 2847, cards: 156 },
    format: 'git',
    updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'repo-torvalds-linux',
    type: 'repo',
    name: 'torvalds/linux',
    subtitle: 'Linus Torvalds · The Linux kernel',
    status: 'ready',
    stats: { entities: 45012, cards: 892 },
    format: 'git',
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'repo-nodejs-node',
    type: 'repo',
    name: 'nodejs/node',
    subtitle: 'Node.js Foundation · JavaScript runtime',
    status: 'ready',
    stats: { entities: 3421, cards: 234 },
    format: 'git',
    updatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  // Documents
  {
    id: 'doc-platform-rfc',
    type: 'document',
    name: 'Platform RFC v3.pdf',
    subtitle: 'PDF · 28 pages · Platform Architecture',
    status: 'ready',
    stats: { entities: 28, cards: 12 },
    format: 'pdf',
    updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-service-catalog',
    type: 'document',
    name: 'service-catalog.xlsx',
    subtitle: 'Excel · 5 sheets · Service registry',
    status: 'ready',
    stats: { entities: 87, cards: 18 },
    format: 'xlsx',
    updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-oncall-runbook',
    type: 'document',
    name: 'oncall-runbook.md',
    subtitle: 'Markdown · 12 pages · On-call procedures',
    status: 'ready',
    stats: { entities: 12, cards: 8 },
    format: 'md',
    updatedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-api-spec',
    type: 'document',
    name: 'API Specification.pdf',
    subtitle: 'PDF · 45 pages · REST API Reference',
    status: 'indexing',
    progress: 67,
    stats: { entities: 45, cards: 22 },
    format: 'pdf',
    updatedAt: new Date().toISOString(),
  },
]

export const MOCK_CARDS: KnowledgeCard[] = [
  {
    ref: 'hf-transformers-tokenizer',
    title: 'Tokenizer: BPE to SentencePiece',
    status: 'verified',
    markdown: `# Tokenizer Architecture

The tokenizer layer in transformers implements multiple strategies for subword segmentation:

- **BPE (Byte-Pair Encoding)**: Iterative merging of frequent byte pairs
- **WordPiece**: Maximizing likelihood of vocabulary
- **SentencePiece**: Language-independent approach

## Usage

\`\`\`python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
tokens = tokenizer.encode("Hello, world!")
\`\`\`

## Performance

- Token limit: typically 512–4096
- Vocabulary size: 30K–100K tokens
- Encoding time: <1ms per sample`,
    provenance: [
      {
        ref: 'huggingface/transformers',
        kind: 'code',
        loc: 'src/transformers/tokenization_utils.py:45',
      },
      {
        ref: 'huggingface/transformers',
        kind: 'code',
        loc: 'src/transformers/models/bert/tokenization_bert.py:120',
      },
    ],
    relations: [
      { kind: 'depends-on', ref: 'hf-transformers-model-architecture' },
      { kind: 'part-of', ref: 'hf-transformers-pipeline' },
    ],
  },
  {
    ref: 'hf-transformers-model-architecture',
    title: 'Model Architecture: Transformer Decoder',
    status: 'verified',
    markdown: `# Transformer Architecture

The core transformer architecture following Vaswani et al. (2017).

## Encoder Stack

- Multi-head attention (8–16 heads)
- Feed-forward networks (hidden_size × 4)
- Layer normalization + residual connections

## Decoder Stack

- Masked self-attention
- Cross-attention to encoder
- Feed-forward with gating

## Key Parameters

- \`hidden_size\`: 768–1024
- \`num_layers\`: 12–24
- \`attention_heads\`: 8–16`,
    provenance: [
      {
        ref: 'huggingface/transformers',
        kind: 'code',
        loc: 'src/transformers/models/bert/modeling_bert.py:200',
      },
    ],
    relations: [
      { kind: 'references', ref: 'hf-transformers-tokenizer' },
    ],
  },
  {
    ref: 'platform-rfc-api-gateway',
    title: 'API Gateway: Request Routing',
    status: 'verified',
    markdown: `# API Gateway Architecture

The platform API gateway handles routing, rate limiting, and authentication.

## Components

1. **Router**: Directs requests by service
2. **Rate Limiter**: Token bucket (100 req/min per user)
3. **Auth**: JWT validation + RBAC

## Configuration

See \`/api-gateway/config.yaml\` for routing rules.`,
    provenance: [
      {
        ref: 'Platform RFC v3.pdf',
        kind: 'pdf',
        loc: 'p.8',
      },
      {
        ref: 'Platform RFC v3.pdf',
        kind: 'pdf',
        loc: 'p.9',
      },
    ],
    relations: [],
  },
  {
    ref: 'service-catalog-analytics',
    title: 'Analytics Service: Metrics Collection',
    status: 'draft',
    markdown: `# Analytics Service

Collects and aggregates metrics from all platform services.

## Data Model

- Events: impressions, conversions, errors
- Aggregation: 1-minute, hourly, daily buckets
- Retention: 90 days hot, 1 year cold

## Integration

Services POST to \`/metrics\` endpoint with schema validation.`,
    provenance: [
      {
        ref: 'service-catalog.xlsx',
        kind: 'xlsx',
        loc: 'Sheet1!B4',
      },
    ],
    relations: [
      { kind: 'depends-on', ref: 'service-catalog-postgres' },
    ],
  },
]

export const MOCK_ANSWER = {
  answer:
    'The tokenizer layer in transformers implements BPE, WordPiece, and SentencePiece strategies for subword segmentation. BPE iteratively merges frequent byte pairs, WordPiece maximizes likelihood, and SentencePiece is language-independent. Standard configurations use a vocabulary of 30K–100K tokens and can encode 512–4096 tokens per sample.',
  claims: [
    {
      text: 'BPE iteratively merges frequent byte pairs',
      source: 'huggingface/transformers',
      file: 'src/transformers/tokenization_utils.py',
      start_line: 45,
      end_line: 50,
      confidence: 0.92,
    },
    {
      text: 'Vocabulary size is typically 30K–100K tokens',
      source: 'Platform RFC v3.pdf',
      confidence: 0.88,
    },
  ],
  confidence: 0.89,
  route_used: 'vector_search → tree_descent → grounding',
  status: 'success',
  suggestions: [
    'How does BPE differ from WordPiece?',
    'What is SentencePiece and why use it?',
    'How to implement a custom tokenizer?',
  ],
}

export const MOCK_SUBGRAPH = {
  nodes: [
    // L4 Domains (top layer, arranged in inner circle)
    { id: 'domain-nlp', label: 'NLP', layer: 'L4', _x: -40, _y: -50, _z: -150 },
    { id: 'domain-ml', label: 'Machine Learning', layer: 'L4', _x: 40, _y: -50, _z: -150 },
    { id: 'domain-data', label: 'Data Pipeline', layer: 'L4', _x: 0, _y: 40, _z: -150 },

    // L3 Cards (middle layer, arranged in middle circle)
    { id: 'card-tokenizer', label: 'Tokenizer Design', layer: 'L3', _x: -60, _y: -30, _z: 0 },
    { id: 'card-attention', label: 'Attention Mechanism', layer: 'L3', _x: 60, _y: -30, _z: 0 },
    { id: 'card-embeddings', label: 'Embeddings', layer: 'L3', _x: 0, _y: 60, _z: 0 },
    { id: 'card-pipeline', label: 'Data Pipeline', layer: 'L3', _x: -60, _y: 30, _z: 0 },
    { id: 'card-training', label: 'Training Loop', layer: 'L3', _x: 60, _y: 30, _z: 0 },

    // L1 Sources (bottom layer, arranged in outer circle)
    { id: 'src-tokenizer-py', label: 'tokenization_utils.py', layer: 'L1', _x: -90, _y: -40, _z: 150 },
    { id: 'src-tokenizer-bpe', label: 'BPE Encoder', layer: 'L1', _x: -45, _y: -80, _z: 150 },
    { id: 'src-models', label: 'models/__init__.py', layer: 'L1', _x: 90, _y: -40, _z: 150 },
    { id: 'src-attention', label: 'attention.py', layer: 'L1', _x: 45, _y: -80, _z: 150 },
    { id: 'src-embeddings', label: 'embeddings.py', layer: 'L1', _x: 0, _y: 100, _z: 150 },
    { id: 'src-pipeline', label: 'data_pipeline.py', layer: 'L1', _x: -90, _y: 40, _z: 150 },
    { id: 'src-training', label: 'training.py', layer: 'L1', _x: 90, _y: 40, _z: 150 },
    { id: 'src-utils', label: 'utils.py', layer: 'L1', _x: 0, _y: -100, _z: 150 },
  ],
  edges: [
    // Intra-layer edges
    // L4 edges
    { s: 'domain-nlp', d: 'domain-ml', kind: 'relates-to', layer: 'L4', inter: false },
    { s: 'domain-ml', d: 'domain-data', kind: 'relates-to', layer: 'L4', inter: false },

    // L3 edges
    { s: 'card-tokenizer', d: 'card-embeddings', kind: 'references', layer: 'L3', inter: false },
    { s: 'card-attention', d: 'card-embeddings', kind: 'uses', layer: 'L3', inter: false },
    { s: 'card-pipeline', d: 'card-training', kind: 'feeds', layer: 'L3', inter: false },

    // L1 edges
    { s: 'src-tokenizer-py', d: 'src-tokenizer-bpe', kind: 'imports', layer: 'L1', inter: false },
    { s: 'src-tokenizer-py', d: 'src-utils', kind: 'imports', layer: 'L1', inter: false },
    { s: 'src-attention', d: 'src-utils', kind: 'imports', layer: 'L1', inter: false },
    { s: 'src-embeddings', d: 'src-utils', kind: 'imports', layer: 'L1', inter: false },
    { s: 'src-training', d: 'src-pipeline', kind: 'calls', layer: 'L1', inter: false },
    { s: 'src-models', d: 'src-attention', kind: 'exports', layer: 'L1', inter: false },

    // Inter-layer edges (sources -> cards)
    { s: 'src-tokenizer-py', d: 'card-tokenizer', kind: 'derived', layer: 'L1', inter: true },
    { s: 'src-tokenizer-bpe', d: 'card-tokenizer', kind: 'derived', layer: 'L1', inter: true },
    { s: 'src-attention', d: 'card-attention', kind: 'derived', layer: 'L1', inter: true },
    { s: 'src-embeddings', d: 'card-embeddings', kind: 'derived', layer: 'L1', inter: true },
    { s: 'src-pipeline', d: 'card-pipeline', kind: 'derived', layer: 'L1', inter: true },
    { s: 'src-training', d: 'card-training', kind: 'derived', layer: 'L1', inter: true },

    // Inter-layer edges (cards -> domains)
    { s: 'card-tokenizer', d: 'domain-nlp', kind: 'part-of', layer: 'L3', inter: true },
    { s: 'card-attention', d: 'domain-nlp', kind: 'part-of', layer: 'L3', inter: true },
    { s: 'card-embeddings', d: 'domain-nlp', kind: 'part-of', layer: 'L3', inter: true },
    { s: 'card-pipeline', d: 'domain-data', kind: 'part-of', layer: 'L3', inter: true },
    { s: 'card-training', d: 'domain-ml', kind: 'part-of', layer: 'L3', inter: true },
  ],
}
