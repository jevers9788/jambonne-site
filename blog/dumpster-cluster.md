# Dumpster Cluster

There was once a time when I worked at a large, well-resourced, AI-forward tech company. We ran our infrastructure on GCP and had a team of Google employees at our beck and call whenever compute needs arose. A similar arrangement was in place with NVIDIA, which granted us access to new hardware as it rolled off the production line. Securing greater numbers of more powerful accelerators was typically a matter of sending a Slack message and having a few meetings.

More recently, building out a bootstrapped startup, I've learned what life is like among the compute have-nots. GPU procurement is difficult. Large numbers of accelerators are locked up in committed-use contracts with the big dog customers. If you can get capacity at all, the costs seem extra gruesome when it's me, instead of a corporate finance team, who gets the bill.

I'm not the only one feeling the pinch. Lots of small companies are realizing that balancing dollars spent on GPUs against value produced by tokens is an increasingly high priority, and getting creative with their solutions. There are neoclouds, but they have enough problems of their own that I doubt their viability as a place to lay the foundations of an organization's compute infrastructure. But where else is there to look?

## GPUs Out to Pasture

All of these GPU chips are sitting in data centers somewhere. Those buildings can only fit so many racks. NVIDIA is putting out new hardware on an accelerated release cycle: after years of launching a new data-center architecture roughly every two years (Volta, Ampere, Hopper, Blackwell), in 2024 it picked up the pace and moved to a yearly cadence, with Blackwell Ultra following in 2025 and Rubin in 2026.

There's only so much room in the data centers, and cloud providers are going to make sure those new units have space. So eventually some of the older resident machines are going to be given the "out with the old, in with the new!" treatment.

What happens to the old GPUs cast out of their former homes? In the near term, they end up on the secondary market. Cloud providers rarely sell old hardware themselves; they pass it to disposal firms that wipe, test, and resell it in bulk. For small buyers, much of it ends up on eBay, where you can buy a single card with buyer protection and compare prices across sellers.

On paper, hyperscalers depreciate their servers over five to six years, but GPUs usually get switched out after two to four years of use, since each new generation makes the old one uneconomical to keep running. When racks with legacy hardware are retired, the chips are often still functional.

## Introducing the Dumpster Cluster

At first blush, an eBay GPU doesn't sound much better than a neocloud GPU (though they're often one and the same — you're just paying the neocloud for an eBay GPU). But what kind of potential remains in old hardware? A group of researchers set out to answer this question. They've released their findings in a [paper](https://arxiv.org/abs/2608.14614). It describes a GPU server rack in which every component was purchased on eBay, charmingly referred to as "the dumpster cluster." The authors compare a retiree cluster against the latest in the Hopper and Blackwell families, measuring success along the axes of total tokens generated, capital expenditure, and carbon emissions.

<table class="prices">
<caption>The 128× V100 dumpster cluster vs. an 8× B200 system, as reported in the paper</caption>
<thead><tr><th></th><th>V100 pod</th><th>8× B200</th></tr></thead>
<tr><td>Hardware cost</td><td><span class="rainbow">~$22K</span></td><td>~$600K</td></tr>
<tr><td>LLaMA-8B prefill</td><td><span class="rainbow">223,936 tok/s</span></td><td>62,651 tok/s</td></tr>
<tr><td>LLaMA-8B decode</td><td><span class="rainbow">8,128 tok/s</span></td><td>26,037 tok/s</td></tr>
<tr><td>LLaMA-70B prefill</td><td><span class="rainbow">1,512 tok/s</span></td><td>37,045 tok/s</td></tr>
<tr><td>LLaMA-70B decode</td><td><span class="rainbow">2,536 tok/s</span></td><td>24,695 tok/s</td></tr>
</table>

There are some actual upsides to the approach. The whole 128-GPU pod cost about $22K (as of March 2026), vs. roughly $600K for an 8× B200 system. They got the V100 cards for $60 each. Reliability was surprisingly good: over a year of operation, the authors logged 58 incidents, only 8 of them hardware failures (and just one of those a GPU); most of the rest were recoverable PCIe and software resets.

Supply is plentiful for now, though a run through eBay suggests that $60 V100s are harder to come by in October 2026. On small models, the old hardware holds its own: for LLaMA-8B doing prefill, the paper reports the V100 pod beating the B200 system. By the measure of embodied carbon (the emissions already spent manufacturing a chip), keeping these cards running is a better use of them than sending them to a landfill. The authors also did a lot of engineering to get there, most notably a custom Rust serving engine that splits the model pipeline-parallel style and has the CPUs handle communication between stages asynchronously, so the GPUs never stop computing to launch NCCL transfers.

## Dumpster Cluster, with Emphasis on the "Dumpster"

Obstacles emerge, however, when a bigger model is put into play. As is becoming clear even on new hardware, bandwidth tends to be the bottleneck in ML workloads, and the V100 doesn't have much of it: 900 GB/s of memory bandwidth against an H100's 3,350 GB/s, and 300 GB/s NVLink against 900 GB/s.

The pipeline parallelism required for splitting up the model means a lot of sluggish trips across the wire. On 70B, the V100 pod trails the 8× B200 system by roughly 24× on prefill and 10× on decode.

Recycling hardware isn't an environmental panacea either. The V100 is built on an older 12 nm process, with far less densely packed transistors than the 4 nm H100, so it spends more energy on every token.

On grid-average electricity, the authors estimate about 4× the carbon per token of new hardware for 8B models and over 40× for 70B, far more than the embodied carbon saved by reusing the chips. That totally obliterates any notion I had that this was a more environmentally friendly approach.

Finally, cost-effectiveness depends entirely on grid pricing and energy mix. With cheap Chinese grid power (also mostly coal-produced and environmentally hostile), the V100 pod is up to 6× more cost-effective than H100s for 8B models, but for 70B that advantage goes away, and the V100s reach only about two-thirds of an H100's cost efficiency over three years.

Strictly speaking, the energy mix matters a lot for carbon, while the price of electricity sets the cost. The two travel together, though, because the mix of sources (coal, gas, hydro, solar) largely determines what power costs in a region.

The paper's scenarios show the tradeoff: China has the cheapest power (about $0.056/kWh) but the dirtiest (584 gCO2/kWh), while Brazil's is far cleaner (97 gCO2/kWh) but more than twice the price ($0.125/kWh). An old cluster runs crazy hot and looks best on cost exactly where electricity is dirtiest, so if you care at all about the environmental impact of AI (I think you should!), this is an approach to consider carefully.

## Whither the Dumpster Cluster?

In one sense, the outlook for small-scale, budget inference enthusiasts isn't optimistic. You can run a decently powerful model on legacy hardware, but the price you pay for that low-capital entry point, privacy, and autonomy is a white-hot carbon-emissions machine that will (a) need a lot of maintenance and (b) need to be replaced and retooled frequently.

_But_ viewed in a more forward-looking sense, a cottage industry of small-scale inference servers could be a good thing. The assembly, engineering, and maintenance experience gained from putting together local or small-scale inference services is valuable process knowledge.

There's also the hope that ingenuity in software design can enhance these systems' capabilities. One thing to note here is that KV cache designs weren't investigated at all in the paper (expect more on this point in future writing). What about speculative decoding? Think of the whole host of careful, model-hardware-specific optimizations in the [DeepInfer kit](/blog/deep-infer).

Finally, the shortcomings of dumpster hardware might be smoothed over by designing the cluster with certain workloads in mind. Splitting prefill and decode into two separate clusters is increasingly common, and similar innovations in the design of a future dumpster cluster could take a similar workload-specific approach. I'm also thinking of the utility for search architectures or models like Jev that skip token-by-token decoding and produce their whole output in a single query. Depending on how things shift in green energy production, dumpster cluster setups could become attractive.
