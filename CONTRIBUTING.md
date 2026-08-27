# Contributing to HYDRA-UMC-COGNITIVE-NODE 🦾

We welcome contributions to the semantic reasoning engine of the HYDRA-UMC platform.

## Technology Stack
- **Language**: Python 3.12.
- **Hardware**: Raspberry Pi CM5, Hailo-10 M.2 AI Accelerator (40 TOPS).
- **Frameworks**: HailoRT, gRPC, Protobuf, Llama-3 (Quantized).
- **Models**: VLA, STT/TTS (Whisper).

## Guidelines
1. **Model Efficiency**: All GenAI models must be quantized for Hailo-10 to ensure low-latency reasoning.
2. **Privacy**: Ensure no data is leaked to external APIs. All processing must remain local.
3. **Safety**: Semantic plans must be validated against the safety zones and motion constraints.
4. **Testing**: Use the `HYDRA-UMC-DOCS-QA` RAG system to verify technical consistency of generated plans.
