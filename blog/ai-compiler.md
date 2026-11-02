# LLMs as Kernel Compilers

Compute kernels have big performance implications for large-scale machine learning systems. The matrix multiplications, attention operations, activations, and normalization functions that make up the bulk of an LLM's work need to execute at a much higher frequency than other parts of the software. If they're slow, you'll know it, and you probably won't like it.

In response to SLO requirements and user expectations, the pace and volume of research in this domain have risen, and methods like FlashAttention, PagedAttention, FlashMLA, and the whole ecosystem of quantized matrix-multiplication kernels do a lot to reduce latency and make efficient use of resources.

Generally speaking, research on kernel development follows advances in hardware. FlashAttention-3, for example, was built around features introduced with Hopper (WGMMA instructions, TMA engine, FP8 tensor cores) and runs only on Hopper chips. Backward compatibility is pursued, but only as far back as Ampere: FlashAttention-2 requires an A100-class GPU or newer, and since late 2024, Triton has only used tensor cores on Ampere and later.

There's a definite but (for anyone without expert knowledge of computers) opaque relationship between software and hardware. On the one hand, physical laws put a ceiling on how fast software can run and how much stuff it can move around in a given period of time. On the other hand, there is [reason to think](https://www.science.org/doi/10.1126/science.aam9744) that creativity in the software domain can leverage the physical hardware beyond prior expectations.

Sometimes, when I'm trying to rent a more economical but still new-ish GPU from a cloud provider, like an L4, hours go by without any machines becoming available. Meanwhile, older GPUs are plentiful. I can't help but wonder whether all of this stock could be put to use.

I was thinking about this while I read "AI as a Compiler," a research [paper](https://arxiv.org/pdf/2609.36800) exploring the use of frontier models for optimized kernel generation. The authors use OpenAI's GPT-6 Astra to generate PTX, NVIDIA's low-level virtual assembly language. Their interest, or how they imagine an agent like this being useful, is dual-purpose: first, to make kernels faster, and second, to reduce software maintenance overhead.

Today, a Triton kernel is lowered through a sequence of intermediate representations (Triton IR → TritonGPU IR → LLVM IR) before it becomes PTX. NVIDIA's assembler then turns that PTX into machine code. Every new architecture feature, such as Hopper's TMA and WGMMA or Blackwell's tensor memory, needs new lowering passes, data layouts, and instruction selection in that chain of intermediate representations, and someone has to keep all of it working.

These are sound motivations, but I was interested in another angle. I wanted to see how well a frontier kernel-compiler agent could adapt newer attention algorithms to older hardware. By generating PTX that targets the older GPU and uses only the instructions it supports, could we get these GPUs to run new algorithms well enough that they could be deployed in production systems?

Motivations here are many. If an organization already has older GPUs, recovering unused performance might extend their useful life. Secondhand data-center GPUs are also cheap, which puts them within reach of students, independent researchers, and labs with limited budgets.

As a practical goal on any large scale, this might be quixotic. Some caveats:

- Using older GPUs can actually be worse for the environment, because they use more energy to do the same work as a newer accelerator and produce more heat and more carbon in the process.
- It might not be cheaper for the person maintaining the systems, either. Devastating electricity bills are a prominent issue in the world of local LLMs.
- Physical laws limit what's possible, in this scenario mostly through memory bandwidth and interconnect latency. There's more about this in the [dumpster cluster writeup](/blog/dumpster-cluster).

These concerns aside, the potential upsides make an experiment worthwhile. My rationale here breaks down simply: (1) we need compute, (2) we have a lot of old compute, and (3) we should find ways to use it instead of piling up more e-waste.

## Research Summary 

Triton's compiler translates kernel code through intermediate representations before producing PTX. Supporting new hardware features requires changes to that pipeline. The paper documents the implemntation of an agent that generates PTX directly, while its evaluation environment assembles, tests, times, and profiles candidates. From there, NVIDIA's assembler and driver turn that PTX into executable GPU code.

The hoped for result is not just faster kernels, but that this approach would make for less work building and maintaining compiler backends. The paper shows competitive kernel results, but it doesn't yet establish that maintaining the whole system, including verification, costs less. A lot rides on frontier intelligence like Astra being inexpensive enough for this to be worth it. 

The paper evaluates L40S, H100, and B200 GPUs -- that includes Ada, Hopper, and Blackwell architecture generations. The Triton version used in my experiment disables tensor-core lowering below sm_80, including V100 and T4, and falls back to scalar multiply-add instructions. [That change](https://github.com/triton-lang/triton/pull/5066) can make matrix-heavy kernels much slower even though the hardware has tensor cores. Other kernels still work, while some fail to compile.

That makes old GPUs an interesting test of the paper's idea: can generated PTX recover capabilities that the compiler no longer uses?

## Experiment Overview

I'll look at three operations, all evaluated in the original paper:

- **GEMV:** matrix-vector multiplication, relevant to processing one token at a time and often limited by memory bandwidth.
- **BitDelta:** matrix multiplication with packed binary weights. A useful kernel must decode those weights as well as multiply them.
- **SageAttention:** attention using quantized queries and keys, an interesting case because the pinned Triton cannot compile it for V100.

GEMV multiplies a 4096-by-4096 matrix by a vector, like one token through a 4096-wide layer. BitDelta processes 4096 rows at once, closer to a large batch or prefill than single-token decoding. SageAttention uses 1024 queries and 128 keys per head, with grouped query heads.

TAIC and its evaluation tools are publicly available. On a V100, I:

1. checked the evaluation pipeline using Triton's own PTX and a handwritten ReLU kernel;
2. measured autotuned Triton and stock PyTorch baselines;
3. ran TAIC to generate candidates, then checked and timed the selected kernels.

Getting this to work required fixes to the released harness and a separate PTX launcher for kernels Triton could not compile. I don't think these changes should affect how we look at the experiment's results, but I'm noting them out of duty to scholarly conscience. There's a link to a GitHub repo with more technical information at the end of the writeup. These checks established that the local pipeline worked, but they didn't reproduce the paper's results. I plan to do that in a follow-up experiment.

## Results

These are exploratory results at fixed shapes, using median latency:

<table class="prices">
<caption>Median latency on a V100</caption>
<thead><tr><th>Kernel</th><th>Triton</th><th>Stock path</th><th>Generated PTX</th></tr></thead>
<tr><td>FP16 GEMV</td><td>0.130 ms</td><td>0.053 ms</td><td><span class="rainbow">0.053 ms</span></td></tr>
<tr><td>BitDelta</td><td>12.67 ms</td><td>2.99 ms</td><td><span class="rainbow">2.27 ms</span></td></tr>
<tr><td>SageAttention</td><td>Does not compile</td><td>2.25 ms</td><td><span class="rainbow">0.271 ms</span></td></tr>
</table>

Some notes on the results:

**GEMV:** the generated kernel matches the measured cuBLAS-backed PyTorch path, about 2.44 times faster than Triton. Matching the recorded medians doesn't establish identical performance under every condition, but it shows that TAIC closed the gap. This was the best candidate tested before the budget ran out, not TAIC's accepted final answer.

**BitDelta:** the stock path already uses cuBLAS, after unpacking the binary weights. The generated kernel uses V100 tensor cores while decoding packed weights, beating unpack-plus-cuBLAS by about 32% and Triton by 5.59 times. cuBLAS on already unpacked FP16 weights takes about 1.92 ms, but requires 16 times the weight storage.

**SageAttention:** Triton's fallback incorrectly applies a floating-point conversion to integer operands, producing invalid compiler IR. This is a bug in Triton's untested pre-Ampere path, not a hardware limit; details are in [the repo's porting notes](https://github.com/jevers9788/taic-experiments/blob/main/PORTING.md) (item 13). The direct launcher bypasses that compilation failure. The generated kernel runs about 8.29 times faster than the tested eager PyTorch reference. That is a gain over this fallback, not a comparison with an optimized attention library or a working Triton implementation.

The paper reports relative speedups rather than the absolute latencies needed for a direct comparison with these V100 timings. Its results therefore don't tell us how this V100 would rank against its newer GPUs on these workloads. That should give pause when reading my results: how much is a 2.44-times speedup on a V100 worth if a newer GPU runs the unoptimized kernel faster still? I haven't measured that yet.

## Limitations

These results are promising enough to motivate more experiments, but several questions remain.

First, I couldn't get my hands on a machine with an Ada-architecture GPU while I was doing this experiment, so I haven't reproduced the paper's results.

Second, my tests were narrow: I ran each generation only once, didn't run model forward passes to measure end-to-end performance, and didn't test varying input shapes. Each of these limits how much the results can tell us.

I also didn't run the paper's symbolic verifier to formally verify correctness. Finally, I didn't try using a historical compiler to see if a prior version of Triton would produce similarly performant PTX.

## What's next

Based on the results of the experiment, my biggest hope is that FP8 storage could help a bandwidth-bound kernel run well on accelerators without native FP8 arithmetic. FP8 moves half as many input bytes as FP16, so a generated kernel could load those bytes and decode them in registers, avoiding a separate conversion pass and a full FP16 copy in memory. That only helps if the saved memory traffic outweighs the decoding work and the numerical accuracy stays stable.

Expect more on this to come. If you're interested in the experiment, the repo with the code is [here](https://github.com/jevers9788/taic-experiments).
