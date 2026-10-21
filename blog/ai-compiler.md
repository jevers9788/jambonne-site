# How Low Can You Go: LLMs as Kernel Compilers

One of the coolest research directions I've seen in a while experiments with replacing some of the kernel compiler stack with LLMs. [AI as a Compiler](https://arxiv.org/pdf/2609.36800) asks whether a model can translate Triton kernels directly into NVIDIA PTX, then improve them using correctness checks and measured performance.

This overlaps with work by companies like [Wafer](https://www.wafer.ai/), which describes optimizing across models, serving engines, kernels, and hardware. The paper studies a narrower boundary: given a specialized Triton kernel, generate PTX that preserves its interface and computation.

## Brief summary of the paper

Triton's compiler translates kernel code through intermediate representations before producing PTX. Supporting new hardware features requires changes to that pipeline. The paper's TAIC agent generates PTX directly, while its TCENV evaluation environment assembles, tests, times, and profiles candidates. NVIDIA's assembler and driver still turn that PTX into executable GPU code.

The ambition is not just faster kernels, but less work building and maintaining compiler backends. The paper demonstrates competitive kernels; it doesn't yet establish that maintaining the whole system, including verification, costs less.

I was interested in another possibility: how much performance could we recover on accelerators that newer compiler versions serve poorly?

The paper evaluates L40S, H100, and B200 GPUs, spanning Ada, Hopper, and Blackwell. The Triton version used in our experiment disables tensor-core lowering below sm80, including V100 and T4, and falls back to scalar multiply-add instructions. [That change](https://github.com/triton-lang/triton/pull/5066) can make matrix-heavy kernels much slower even though the hardware has tensor cores. Other kernels still work, while some fail to compile.

That makes old GPUs an interesting test of the paper's idea: can generated PTX recover capabilities that the compiler no longer uses?

## Why

DeepSeek sparked my interest in this kind of work. It made me realize how little I knew about the performance engineering behind training and serving models.

If an organization already has older GPUs, recovering unused performance might extend their useful life. Whether renting those GPUs is cheaper than using newer hardware is a separate question. I haven't measured availability, cost per token, energy use, or the communication overhead of spreading a workload across more devices.

As a practical goal, this might be quixotic. But I'm interested to see how much of an old GPU's performance is unused, and how much we can recover with PTX written expressly for that hardware.

I'll look at three operations, all evaluated in the original paper:

- **GEMV:** matrix-vector multiplication, relevant to processing one token at a time and often limited by memory bandwidth.
- **BitDelta:** matrix multiplication with packed binary weights. A useful kernel must decode those weights as well as multiply them.
- **SageAttention:** attention using quantized queries and keys, an interesting case because the pinned Triton cannot compile it for V100.

GEMV multiplies a 4096-by-4096 matrix by a vector, like one token through a 4096-wide layer. BitDelta processes 4096 rows at once, closer to a large batch or prefill than single-token decoding. SageAttention uses 1024 queries and 128 keys per head, with grouped query heads.

## My experiment

TAIC and its evaluation tools are publicly available. On a V100, I:

- checked the evaluation pipeline using Triton's own PTX and a handwritten ReLU kernel;
- measured autotuned Triton and stock PyTorch baselines;
- ran TAIC to generate candidates, then checked and timed the selected kernels.

Getting this to work required fixes to the released harness and a separate PTX launcher for kernels Triton could not compile. These checks established that the local pipeline worked; they did not reproduce the paper's results on its hardware.

## Results

These are exploratory results at fixed shapes, using median latency:

| Kernel | Triton | Stock path | Generated PTX |
|---|---:|---:|---:|
| FP16 GEMV | 0.130 ms | 0.053 ms | 0.053 ms |
| BitDelta | 12.67 ms | 2.99 ms | 2.27 ms |
| SageAttention | Does not compile | 2.25 ms | 0.271 ms |

**GEMV:** the generated kernel matches the measured cuBLAS-backed PyTorch path, about 2.44 times faster than Triton. Matching the recorded medians doesn't establish identical performance under every condition, but it shows that TAIC closed this particular gap. This was the best tested candidate before the budget ran out, not TAIC's accepted final answer.

**BitDelta:** the stock path already uses cuBLAS, after unpacking the binary weights. The generated kernel uses V100 tensor cores while decoding packed weights, beating unpack-plus-cuBLAS by about 32% and Triton by 5.59 times. cuBLAS on already unpacked FP16 weights takes about 1.92 ms, but requires 16 times the weight storage. The useful result is improving the compressed-weight path, not beating standalone cuBLAS.

**SageAttention:** Triton's fallback incorrectly applies a floating-point conversion to integer operands, producing invalid compiler IR. Our launcher bypasses that compilation failure. The repaired generated kernel runs about 8.29 times faster than the tested eager PyTorch reference. That is a gain over this fallback, not a comparison with an optimized attention library or a working Triton implementation.

The paper reports relative speedups rather than the absolute latencies needed for a direct comparison with these V100 timings. Its results therefore don't tell us how this V100 would rank against its newer GPUs on these workloads.

## Limitations

These results give me reasons to keep experimenting, but several questions remain:

- **No modern-GPU control.** I couldn't obtain an L4, so I haven't tested the setup on a supported architecture. An L4 would be an Ada control, not an exact reproduction of the paper's L40S results.
- **One search sequence per kernel.** Generation is stochastic, and there are no independent repeats here. The paper repeated four B200 workloads five times; most of its broader grid also used single runs.
- **One shape per kernel.** Each kernel is compiled for a fixed size. These isolated cases don't establish performance across production workloads.
- **A different baseline for SageAttention.** It uses PyTorch and our launcher. The inherited output fields still say `triton` in this mode, so those labels must not be taken literally.
- **No historical-compiler control.** Comparing with a Triton version that still lowers these operations to tensor cores would help distinguish recovered compiler performance from additional optimization. Simply removing a guard is not enough to assume the old path works correctly.
- **Tested, not proven.** Numerical tests and NVIDIA's memory and race checkers provide meaningful but finite coverage. We did not use the paper's Volta symbolic verifier (distinct from the V100's Volta hardware architecture). Racecheck caught a real race in the first SageAttention kernel; the repaired result passed. SageAttention's numerical check also relies on the upstream PyTorch reference rather than an independent implementation.
- **Environment deviations.** V100 required a CUDA 12 PyTorch build. I fixed released-tool bugs at runtime, and the FP16 GEMM and FlashAttention prompt hints do not activate in the pinned release, so those prompts may differ from the paper's.
- **Kernels, not models.** I haven't measured end-to-end model speed, operating cost, or energy use.

## What I'd like to test next

One hypothesis is that FP8 storage could help a bandwidth-bound kernel even without native FP8 arithmetic. It moves half as many input bytes as FP16. A generated kernel could load those bytes and decode them in registers, avoiding a separate conversion pass and a full FP16 copy in memory.

That only helps if the saved memory traffic outweighs the decoding work and the numerical accuracy is acceptable. It could beat the latency of an FP16 implementation; it would not exceed the GPU's physical memory-bandwidth limit. We haven't demonstrated this yet.
