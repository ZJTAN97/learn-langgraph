`values` column of `thread` table which represents the messages

```json
{
  messages: [
    {
      id: "19fdea79-f352-4058-96bc-4ab6bb23075e",
      name: null,
      type: "human",
      content: "What is LangGraph in one sentence?",
      additional_kwargs: {},
      response_metadata: {},
    },
    {
      id: "lc_run--019d7fd1-61d3-76b1-9187-5d0333b7d367-0",
      name: null,
      type: "ai",
      content:
        "LangGraph is an AI-powered tool that enables users to build and manage knowledge graphs by leveraging natural language processing to convert unstructured data into structured, interconnected information.",
      tool_calls: [],
      usage_metadata: {
        input_tokens: 25,
        total_tokens: 58,
        output_tokens: 33,
        input_token_details: { audio: 0, cache_read: 0 },
        output_token_details: { audio: 0, reasoning: 0 },
      },
      additional_kwargs: { refusal: null },
      response_metadata: {
        id: "gen-1775965922-mlxslkXn6VfcQsaB0JgW",
        logprobs: null,
        model_name: "openai/gpt-4o-mini",
        token_usage: {
          cost: 0.00002355,
          is_byok: false,
          cost_details: {
            upstream_inference_cost: 0.00002355,
            upstream_inference_prompt_cost: 0.00000375,
            upstream_inference_completions_cost: 0.0000198,
          },
          total_tokens: 58,
          prompt_tokens: 25,
          completion_tokens: 33,
          prompt_tokens_details: {
            audio_tokens: 0,
            video_tokens: 0,
            cached_tokens: 0,
            cache_write_tokens: 0,
          },
          completion_tokens_details: {
            audio_tokens: 0,
            image_tokens: 0,
            reasoning_tokens: 0,
            accepted_prediction_tokens: null,
            rejected_prediction_tokens: null,
          },
        },
        finish_reason: "stop",
        model_provider: "openai",
        system_fingerprint: "fp_eb37e061ec",
      },
      invalid_tool_calls: [],
    },
  ],
};
```