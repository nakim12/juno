import Link from "next/link";
import { HeroSection } from "@/components/motion/HeroSection";
import { Navbar } from "@/components/motion/Navbar";
import { Intro } from "@/components/motion/Intro";
import { Reveal } from "@/components/motion/Reveal";
import { SpotlightCard } from "@/components/motion/SpotlightCard";
import { ShinyText } from "@/components/motion/ShinyText";
import { CountUp } from "@/components/motion/CountUp";
import { AmbientBackdrop } from "@/components/motion/AmbientBackdrop";
import { WordReveal } from "@/components/motion/WordReveal";
import { Magnetic } from "@/components/motion/Magnetic";

const GITHUB_URL = "https://github.com/nakim12/juno";

const pillars = [
  {
    tag: "The Tool",
    title: "A copilot that actually reasons about your model",
    body: "A multi-agent chat system that interprets MMM outputs, generates prioritized recommendations, and answers follow-up questions — every claim grounded in the model output or a cited methodology source.",
  },
  {
    tag: "The Proof",
    title: "An evaluation framework that quantifies trust",
    body: "A benchmark suite stress-tests the agent against ground-truth MMM scenarios using an LLM-as-judge, scoring accuracy, calibration, groundedness, and hallucination rate — so the advice is measurably trustworthy, not just plausible.",
  },
];

const features = [
  {
    title: "Grounded reasoning",
    body: "Values come from the parsed model; methodology comes from a cited knowledge base. Nothing is invented.",
  },
  {
    title: "Explicit confidence",
    body: "Every interpretation and recommendation carries a high / medium / low confidence with a one-line rationale.",
  },
  {
    title: "Multi-agent router",
    body: "Questions are classified and dispatched to specialized handlers — interpretation, recommendation, uncertainty, and more.",
  },
  {
    title: "Retrieval-augmented",
    body: "Hybrid retrieval over a curated corpus of MMM methodology grounds the agent's reasoning in real sources.",
  },
  {
    title: "LLM-as-judge",
    body: "A stronger model grades the agent on six dimensions, validated against hand-scored references.",
  },
  {
    title: "Failure-mode catalog",
    body: "Low-scoring responses are logged and categorized into a growing taxonomy of where the agent breaks.",
  },
];

const steps = [
  {
    n: "01",
    title: "Load an MMM output",
    body: "Pick a pre-loaded sample or upload your own model JSON to start in seconds.",
  },
  {
    n: "02",
    title: "Read the analysis",
    body: "Juno streams a structured report: overview, per-channel reads, risks, and ranked recommendations.",
  },
  {
    n: "03",
    title: "Chat about it",
    body: "Ask what to do, what if, or how confident you should be — grounded, cited answers every time.",
  },
];

const dimensions = [
  { label: "Accuracy", prefix: "> ", value: 0.85, decimals: 2, suffix: "" },
  { label: "Calibration", prefix: "ECE < ", value: 0.1, decimals: 2, suffix: "" },
  { label: "Groundedness", prefix: "> ", value: 0.9, decimals: 2, suffix: "" },
  { label: "Actionability", prefix: "> ", value: 4.0, decimals: 1, suffix: " / 5" },
  { label: "Failure recall", prefix: "> ", value: 0.75, decimals: 2, suffix: "" },
  { label: "Hallucination", prefix: "< ", value: 0.05, decimals: 2, suffix: "" },
];

function SectionMarker({ index, label }: { index: string; label: string }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span className="mono text-xs text-accent">{index}</span>
      <span className="h-px flex-1 bg-border" />
      <span className="eyebrow">{label}</span>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="relative overflow-hidden">
      <Intro />

      <AmbientBackdrop />

      <Navbar />

      {/* Hero — full screen with scroll-linked parallax + scale */}
      <HeroSection />

      {/* Showcase — the tool in action */}
      <section id="showcase" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-24">
        <div className="grid items-center gap-14 lg:grid-cols-[0.95fr_1.05fr]">
          <Reveal>
            <div>
              <div className="eyebrow mb-4">the copilot</div>
              <h2 className="display text-4xl font-semibold">
                <WordReveal
                  parts={[
                    { text: "Grounded reads," },
                    { text: "not guesses", className: "gradient-text" },
                  ]}
                />
              </h2>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
                Juno is an agentic copilot that interprets MMM outputs, recommends what to
                do next, and — uniquely — ships with an evaluation framework that quantifies
                whether its advice can actually be trusted.
              </p>
            </div>
          </Reveal>

          {/* Illustrative product panel */}
          <Reveal delay={0.15} className="card relative overflow-hidden shadow-2xl shadow-black/40">
            <div className="scan-line pointer-events-none z-10" />
            <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-400/70" />
              <ShinyText
                text="analysis · six_channel_with_saturation"
                className="mono ml-2 text-[0.7rem]"
              />
            </div>
            <div className="space-y-3 p-5">
              {[
                { name: "Affiliate", roi: "4.5x", conf: "high", tone: "text-success border-[hsl(var(--success)/0.4)] bg-[hsl(var(--success)/0.14)]" },
                { name: "Search", roi: "2.9x", conf: "high", tone: "text-success border-[hsl(var(--success)/0.4)] bg-[hsl(var(--success)/0.14)]" },
                { name: "TikTok", roi: "1.7x", conf: "low", tone: "text-error border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)]" },
              ].map((c, i) => (
                <div
                  key={c.name}
                  className="flex items-center justify-between rounded-lg border border-border bg-background/50 px-4 py-3"
                >
                  <div className="flex items-baseline gap-3">
                    <span className="font-medium">{c.name}</span>
                    <span className="mono text-xs text-muted-foreground">ROI {c.roi}</span>
                  </div>
                  <span
                    className={`pill-pulse mono rounded-full border px-2 py-0.5 text-[0.65rem] ${c.tone}`}
                    style={{ animationDelay: `${i * 1.2}s` }}
                  >
                    {c.conf}
                  </span>
                </div>
              ))}
              <div className="rounded-lg border border-border bg-muted/40 p-4">
                <div className="eyebrow mb-1">grounding · uncertainty</div>
                <p className="text-sm text-muted-foreground">
                  “TikTok’s ROI credible interval is wide (0.6–2.8); treat the ranking
                  as provisional and validate with a lift test.”
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Two pillars */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <SectionMarker index="01" label="Two pieces of equal weight" />
        <div className="grid gap-6 md:grid-cols-2">
          {pillars.map((p, i) => (
            <Reveal key={p.tag} delay={i * 0.08}>
              <SpotlightCard className="card h-full p-8 transition hover:border-accent/60">
                <div className="mb-4 flex items-center justify-between">
                  <span className="mono text-xs uppercase tracking-widest text-accent">
                    {p.tag}
                  </span>
                  <span className="mono text-xs text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="display text-2xl font-semibold">{p.title}</h3>
                <p className="mt-4 leading-relaxed text-muted-foreground">{p.body}</p>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <SectionMarker index="02" label="Capabilities" />
        <h2 className="display max-w-2xl text-4xl font-semibold">
          <WordReveal parts="Built like a production AI system" />
        </h2>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Not a cool demo — a system with the guardrails that separate a copilot from a
          confident guesser.
        </p>
        <Reveal className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <SpotlightCard
              key={f.title}
              className="bg-background p-7 transition hover:bg-surface"
            >
              <span className="mono text-xs text-accent">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
            </SpotlightCard>
          ))}
        </Reveal>
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl px-6 py-20">
        <SectionMarker index="03" label="How it works" />
        <div className="grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.n} delay={i * 0.08}>
              <SpotlightCard className="card h-full p-7">
                <div className="mono display text-4xl font-bold text-transparent [-webkit-text-stroke:1px_hsl(var(--accent))]">
                  {s.n}
                </div>
                <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Evaluation strip */}
      <section id="eval" className="mx-auto max-w-6xl px-6 py-20">
        <SectionMarker index="04" label="Evaluation" />
        <Reveal className="card hero-glow block overflow-hidden p-10">
          <h2 className="display max-w-2xl text-4xl font-semibold">
            <WordReveal parts="Measured on six defensible dimensions" />
          </h2>
          <p className="mt-4 max-w-2xl text-muted-foreground">
            A benchmark suite generated from ground-truth MMM scenarios grades every
            response — so quality is a number you can point at, not a vibe.
          </p>
          <div className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-3 lg:grid-cols-6">
            {dimensions.map((d) => (
              <div key={d.label} className="bg-background p-5 text-center">
                <div className="text-sm font-semibold">{d.label}</div>
                <CountUp
                  to={d.value}
                  decimals={d.decimals}
                  prefix={d.prefix}
                  suffix={d.suffix}
                  className="mono mt-2 block text-xs text-accent"
                />
              </div>
            ))}
          </div>
          <Link
            href="/evaluation"
            className="mono mt-8 inline-flex items-center gap-2 text-sm text-accent transition hover:opacity-80"
          >
            See the latest benchmark results →
          </Link>
        </Reveal>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <Reveal>
        <SpotlightCard className="card hero-glow block p-14 text-center">
          <h2 className="display text-4xl font-semibold">
            <WordReveal parts="See what your MMM is really saying" />
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Load a sample model and start a grounded conversation in under 30 seconds.
          </p>
          <Magnetic className="mt-9">
            <Link
              href="/analyze"
              className="inline-block rounded-xl bg-gradient-to-br from-accent to-accent-2 px-7 py-3.5 text-sm font-semibold text-background shadow-lg shadow-accent/25 transition hover:opacity-90"
            >
              Launch the demo →
            </Link>
          </Magnetic>
        </SpotlightCard>
        </Reveal>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/70">
        <div className="mono mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 text-xs text-muted-foreground sm:flex-row">
          <span>© {new Date().getFullYear()} juno · mmm copilot</span>
          <div className="flex gap-6">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="hover:text-foreground">
              github
            </a>
            <Link href="/analyze" className="hover:text-foreground">
              demo
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
