# Quick Notes on DeepInfer

DeepInfer is DeepSeek's open-source library for running its latest Flash model, DeepSeek V4.1 Flash. Always eager to see what kinds of tricks the DeepSeek team is doing with inference engineering, I read the [release post](https://zhuanlan.zhihu.com/p/2095560295930508953) on Zhihu and an accompanying [Q&A doc](https://github.com/deepseek-ai/DeepInfer/blob/main/doc/inference_deployment_qa.md). I was gratified to find some cool engineering work, but there are other things to focus on here.

The release is equal parts directional communication, marketing, and technical design. Anyone hoping for a batteries-included way to stand up a production inference provider will be disappointed. Code to tie load balancers, external KV cache storage, and inference replicas together isn't included. The authors explain that components not included in the open-sourced materials were too tightly tied to DeepSeek's internal infrastructure to be released, though the phrasing here suggests that this may change. What is made available includes an offline inference engine for DeepSeek V4.1 Flash; four kernel libraries (FlashMLA, DeepGEMM, DeepEP, and DeepSelect); an SWA cache that retains recent tokens' attention data; a KV cache engine that manages cache memory on the accelerator; DSpark, for speculative decoding; and an API conversion layer that matches DeepSeek's official API.

Beyond that, we learn what DeepSeek thinks about what inference systems should be. At the start of the Zhihu post, DeepSeek states its goals:

1. Support chips from different manufacturers.
2. Organize the software system around a common hardware layout.
3. Retain KV cache data for 72 hours.

Extrapolating from these goals, we could reasonably say that DeepSeek expects the future of the compute ecosystem to be increasingly heterogeneous, and that cost is at the forefront of its design decisions. This latter claim is more important, and it's supported by the fact that both P/D disaggregation and extended KV cache retention are just as much cost-saving measures as they are performance improvements.

On the topic of costs, we're also given revenue figures for providing model inference — something rarely disclosed. Revenue is **<span class="rainbow">$38 per GPU per hour</span>**, calculated at DeepSeek's off-peak API prices. This is revenue, not profit, and we don't know what kind of overhead eats away at that figure. This is a lot more than American labs have released, but for anyone getting starry-eyed (as any number of commenters describing the release as a “money-printing machine” have) we should review the difficult facts of the inference provider business.

I already mentioned the components omitted from this release. The work to fill in the blanks and stand up a production-ready system like what DeepSeek runs internally would require substantial engineering time. All the while, you'll need many Blackwell GPUs (preferably an NVL72 supernode for decode); DeepSeek's smallest efficient unit is **64 prefill + 64 decode GPUs**, plus a KV cache storage cluster.

<table class="prices">
<caption>Renting an 8× B200 VM (A4) from GCP</caption>
<tr><td>3-year commitment</td><td><span class="rainbow">~$57/hr</span></td></tr>
<tr><td>Flex-start</td><td><span class="rainbow">~$64/hr</span></td></tr>
<tr><td>Calendar mode</td><td><span class="rainbow">$90/hr</span></td></tr>
<tr><td>Per GPU</td><td><span class="rainbow">$7–11/hr</span></td></tr>
<tr><td>128 GPUs, before storage and networking</td><td><span class="rainbow">~$900–1,450/hr</span></td></tr>
<tr><td>128 GPUs, monthly</td><td><span class="rainbow">~$0.65–1.05M</span></td></tr>
</table>

<table class="prices">
<caption>Buying hardware to self-host (estimated)</caption>
<tr><td>GB200 NVL72</td><td><span class="rainbow">~$3M</span></td></tr>
<tr><td>GB300 NVL72</td><td><span class="rainbow">~$5M</span></td></tr>
<tr><td>GB300 NVL72, deployed</td><td><span class="rainbow">~$5.7M</span></td></tr>
<tr><td>8× B200 server</td><td><span class="rainbow">~$400–515K</span></td></tr>
<tr><td>Two NVL72 racks, before storage</td><td><span class="rainbow">~$6–11M</span></td></tr>
<tr><td>Operating cost per rack</td><td><span class="rainbow">~$240–410K/yr</span></td></tr>
</table>

If you're DeepSeek, the reported <span class="rainbow">$38 per GPU per hour</span> in revenue beside a rental price of <span class="rainbow">$7–11/hr</span> looks great. If you're already an established inference provider with some traction on OpenRouter or you've got waiting customers elsewhere, this also looks like an attractive proposition. If you're “some guy,” it might not be. Granted, there are more economical ways to get the required compute than the two approaches mentioned here, but you're likely to encounter issues with procurement, volatile pricing, and availability.

The bigger question is where your customers will come from. DeepSeek already has plenty of people using it as an inference provider. Once (if) you have one of these 1.5-ton megaliths under your stewardship, why do people want tokens from you? There's still a tricky business problem waiting on the other end of the engineering work.

I don't mean to deny that DeepInfer presents an opportunity for enterprising inference engineers or companies, however small. Part of what's fun about all of this will be finding out how people do manage to differentiate their deployments.

At the time of writing, DeepInfer has already been forked 2.5k times. There are 176 pull requests open on the repo. Skimming through the open PRs shows us that components withheld from the code are being proposed by many (one might even say too many, but that's a topic for another time) community contributors. I'll look forward to watching the repo to see what the maintainers decide to merge, and how well it all holds up in production.

At the end of the day, the release gives us a few pieces of valuable information. First, KV cache efficiency is solidifying as a top-priority factor in the inference provider business model. Emerging design paradigms are being shaped in accordance with that need. Second, infra and inference engineers will likely — for the present, at least — have to treat the model being served as a primary determining factor in the structure of the system built to serve it. In the future, I'd bet on adapters emerging that can efficiently serve any model on the same system, but for now, designing for the particularities of a given model architecture is necessary. Finally, the economics are a driving factor behind the design in a big way.

I would also like to note that, for whatever else it's worth, DeepInfer has occasioned fantastic memes and statements from Zhihu netizens:

![Zhihu reaction to DeepInfer: a celebratory collage with blue-haired characters.](/static/images/ds-infer-1.png)

![Zhihu reaction to DeepInfer: a raised-fist meme with a DeepSeek flag.](/static/images/ds-infer-2.png)

![Zhihu reaction to DeepInfer: a blue-haired character in a helmet defending the open-source community.](/static/images/ds-infer-3.png)

![Zhihu reaction to DeepInfer: a blue-haired character wearing a golden bowl as a helmet.](/static/images/ds-infer-4.png)
