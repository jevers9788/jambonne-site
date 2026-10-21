# Eyes on DeepInfer


## Intro

* DeepSeek shocks the world; an open source model rivaling western frontier labs, an underwater data center, and now, an open source framework for inference.
* The repo is making its way through social media to wide acclaim. Less widely circulated is a release document on zhihu, which adds motivations and high-level design decisions

## Notes

* Three goals: compatibility with chips from different manufacturers, #2: based on hardware organization for disaggregated prefill and decode, with software built for each stage #3: support storing KV cache for 3 days

* a single cluster (8 cards for prefill x 64-128 nodes for decode * $38 * hour)
  * note: this is not for hobbyists; only B200 and the expensive Huawei Ascend cards 
* encoding/decoding deepseek recipe library; TODO: what does this do?
* four different load balancers; prefill, decode, vision, experts
* also a special storage for KV

## Components

### Token preprocessing
* mostly for security and handling formatting for output?

### Streaming Output Analysis
* state machine to decode the response structure that goes across chunks (output is streamed back in chunks)
* TODO: check out this part of the code, showed up in interview question


## Takeways
* not for hobbyists, expensive, production-grade
* shows that you need to build inference systems for specific models. We knew that this was true of training (models need to be served on the same hardware that they were trained on [TODO: actually true?])

* the comments section is jubilant and amusing

## Questions
* only offline inference open sourced?
