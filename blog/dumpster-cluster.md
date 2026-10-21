# Dumpster Cluster

# Notes
## Watching the economics of compute

- discussions about the AI bubble have zeroed in on hyperscaler bonds
- Claude and OpenAI usage have plateaued
- model output may come to occupy (transitionally or permanently) a commodified state. Value is the buffer between token cost and value gained from those tokens
- NVIDIA is moving fast, but not that fast (market math)
- models move in the other direction (MoE, distillation, other methods of shrinking, performance work for training and inferecne, the entirety of r/locallama
- many worry about the effects of a world "covered in data centers"

## Personal View

- I've worked at large corporations where we have comfortable access to the newest machines, reservations, committed use discounts, etc
- I've also been in the position of having a skimpy budget and zero influence with compute providers
- access to newer compute is both expensive and unreliable
- Older machines are cheap and plentiful

## Reasons not to do this

- beowulf clusters have died down, networking and electricity
- old compute uses more energy than new
- secondary market is subject to supply and demand dynamics

## A Close look at the Dumpster Cluster

* Clouds phase out GPU cards in 3 year cycles
* V100s are on the way out. There are tons of them, and they're cheap
* GPU cards depreciate more quickly as they age
* Operational cost is heavier than new hardware, but most problems are caused by PCIe and software. Only 8 failures over the year that they ran the cluster were because of GPUs
* The performance shortcomings of the cluster are because of bandwidth; decode, which is memory-bound, doesn't do well against modern hardware, but decode-heavy workloads like coding are competitive with state of the art GPUs.
TODO: what else is decode-heavy?
* They did a lot of novel engineering to optimize inference on the dumpster cluster; most notably using the CPU instead of NCCL to transport outputs between layers.
TODO: interested in how this works
* Things start not to look so impressive on the benchmarks for the 70B model; this is where the bandwidth shortcomings become evident
* Running the dumpster cluster isn't energy efficient. V100 chips are smaller, with fewer transistors, so they have to do more work, and consequentially produce more heat.  the paper's authors propose offsetting emissions by running dumpster clusters in settings where renewable energy is available. Sadly for us, such settings do not include the US. The clusters would need to be somewhere far away, where wind power is more plentiful, which would mean a cripplingly long network trip, likely demolishing TTFT and ITL metrics.

## Other Notes
* I'm interested in how KV cache could figure in a dumpster cluster
* I could imagine these being helpful for forward-pass models, BERT or JEV based applications that don't need a decode stage.


# Draft 1

## Intro/Old Hardware
GPUs sit in racks, which are installed in warehouses somewhere. Those warehouses can only fit so many racks. NVIDIA is putting out new hardware on an accelerated release cycle, and when those new machines come out, cloud providers are going to want them in those warehouses. Eventually, some of the older residents of those warehouses are going to be moved out. Where do they go? What do we do with them? When racks with legacy hardware are retired, the chips are often still functional and, for some purposes, useful, so they're sold on the secondary market.
TODO: how do they go from a GCP warehouse to eBay?

## The troubles of compute
Expensive, locked up, weapon in arms race

## Dumpster Cluster
I came across an inspired research paper that answers some of these questions -- inspiringly titled 'the dumpster cluster', every component in the rack was purchased on eBay.
They set out to compare a retiree cluster against the latest in the Hopper and Blackwell family, with success evaluated on axes of total tokens generated, capital expenditure cost, and carbon emissions.

## Obstacles
- as is becoming increasingly clear even in new hardware, bandwidth tends to be the problem in ML workloads. in the dumpster cluster benchmarks, the disparity is more evident for prefill than decode; a performance gap opens.
- recycling hardware isn't an environmental panacea; V100s are smaller chips with less dense transistors, so they have to work harder to produce the same amount of compute as the same number of transistors on newer chip designs, consequently, they generate more heat, and more carbon.
- cost effectiveness is totally dependent on grid pricing and energy mix
TODO: why does energy mix matter for cost?

## Upsides

- capital expenditure is much, much more manageable than new stuff (22k vs 800k)
- reliability is surprisingly good
- supply is plentiful (for now)
- by the environmental of 'embodied carbon', this is a good use of these, better than them going in a landfill?

## Future Investigations and Questions
- I'm fascinated by the relationship between software and hardware. Its only a rarified part of the engineering world that has to think about the substrate, but there are increasing incentives to learn about this -- beyond just the pleasure of understanding how your magical AI application is working from top to bottom. At the frontier, scale may be indispensable, but left behind are many useful things. What can we do with them? 
TODO: historical parallels 

there are no doubt many applications where this kind of stack could be instrumental.
* i'm thinking of forward pass models that don't have a decode step and are less dependent on bandwidth for performance
* hardware constrains are often where we see the most exciting innovations in software. This paper has a few of its own; a custom Rust server, using CPUs instead of NCCL to transport the outputs between pipeline-parallel-split layers,
* what else could be done here? Optimizing LLM inference is proving to be a process that spans all seven leayrs of the application stack. What kinds of benefits could LLM workload routers like llm-d bring? KV caching wasn't mentioned here at all, and with some of the multi-memory tier things like Mooncake, free space in memory outside of VRAM could be useful. Speculative decoding too. What about the whole host of mega optimizations just released in the DeepSeek inference kit? 




