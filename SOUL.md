# Research: summarize about qwen3.5 latest models

## Qwen3.5 Summary

### Model Family
- **Sizes Available**: 0.8B, 2B, 4B, 9B, 27B, 35B, 122B-A10B, 397B-A17B
- **Release Timeline**: First release Feb 2025 (397B-A17B), followed by smaller models in Feb 2026
- **Availability**: Hugging Face Hub, ModelScope, Ollama
- **Type**: Open-source multimodal LLM family

### Key Features & Enhancements
1. **Unified Vision-Language Foundation**: Early fusion training on trillions of multimodal tokens, outperforms Qwen3-VL across reasoning, coding, agents, and visual understanding
2. **Efficient Hybrid Architecture**: Gated Delta Networks + sparse Mixture-of-Experts for high-throughput inference with minimal latency/cost
3. **Scalable RL Generalization**: Million-agent environments with progressively complex task distributions
4. **Global Linguistic Coverage**: 201 languages and dialects supported
5. **Next-Generation Training Infrastructure**: Near-100% multimodal training efficiency, asynchronous RL frameworks

### Technical Capabilities
- **Context Window**: 256k context support (wide search without context management)
- **Inference Modes**: Thinking mode and instruct (non-thinking) mode
- **Agentic Capabilities**: Qwen-Agent, Qwen Code support
- **Multi-modal Input**: Text-only, Image, Video input support

### Available Inference Options
- **Platforms**: Hugging Face Transformers, llm.cpp, MLX (Apple Silicon), SGLang, vLLM
- **Tools**: Unsloth Studio, LM Studio, llama-server
- **Hardware**: Various requirements depending on model size (ranging from 0.8B for personal use to 397B-A17B for enterprise AI clusters)

### Benchmarks
- Official benchmarks available for 35B-A3B, 27B, 122B-A10B, 9B, and 4B models
- Evaluated on: CodeForces, TAU2-Bench, MMLU-ProX (29 languages), WMT24++ (55 languages), MathVision, TIR-Bench, V*
- Benchmark visualizations available for all model sizes

### Source Documents
- GitHub Repository: QwenLM/Qwen3.5
- Hugging Face Collections: Multiple sizes available
- Ollama: Model deployment
- Unsloth: Local inference tutorials

## Summary
Qwen3.5 is Qwen's latest open-source multimodal LLM family featuring significant architectural improvements including Gated Delta Networks mixed with sparse Mixture-of-Experts, unified vision-language foundation training on trillions of tokens, and support for 201+ languages. The family spans from small 0.8B models for local deployment to massive 397B-A17B for enterprise workloads. Key differentiators include 256k context support, dedicated thinking/instruct modes, strong agentic capabilities, and efficient inference infrastructure.
