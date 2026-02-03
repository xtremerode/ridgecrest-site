import Section from "@/components/Section";
import Link from "next/link";
import { site } from "@/data/site";
import { ProjectCard } from "@/components/ProjectCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Custom Residential Design Build Firm | Ridgecrest Designs Pleasanton CA",
  description: "Ridgecrest Designs is a full-service residential design-build firm specializing in luxury homes and remodels across the Tri-Valley area. Schedule your custom design consultation today.",
  alternates: { canonical: "/" },
};

export default function Home() {
  const fp = site.home.featuredProjects;
  return (
    <>
      <Section>
        <div className="grid2">
          <div>
            <div className="kicker">Tri-Valley · California</div>
            <h1>{site.home.headline}</h1>
            <p>{site.home.subhead}</p>
            <div style={{display:"flex", gap:12, flexWrap:"wrap", marginTop:18}}>
              <Link className="btn" href={site.cta.href}>{site.cta.label}</Link>
              <Link className="pill" href="/portfolio">Explore projects</Link>
            </div>
            <div style={{marginTop:28}}>
              <div className="kicker">{site.home.missionTitle}</div>
              <p style={{marginTop:10}}>{site.home.missionBody}</p>
            </div>
          </div>

          <div className="card">
            <img className="img" src={site.images.homeHero} alt="Featured Ridgecrest project" />
          </div>
        </div>
      </Section>

      <Section>
        <div className="kicker">Why choose us</div>
        <h2 style={{marginTop:10}}>A seamless design-build experience</h2>
        <div className="projGrid" style={{marginTop:18}}>
          {site.home.why.map((item) => (
            <div key={item.title} className="card projB">
              <div className="cardPad">
                <div className="kicker">{item.title}</div>
                <p style={{marginTop:10}}>{item.body}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section>
        <div className="kicker">Featured projects</div>
        <h2 style={{marginTop:10}}>Selected work</h2>
        <div className="projGrid" style={{marginTop:18}}>
          <ProjectCard size="A" title={fp[0].title} summary={fp[0].summary} image={fp[0].image} href={fp[0].slug} />
          <ProjectCard title={fp[1].title} summary={fp[1].summary} image={fp[1].image} href={fp[1].slug} />
          <ProjectCard title={fp[2].title} summary={fp[2].summary} image={fp[2].image} href={fp[2].slug} />
        </div>
        <div style={{marginTop:18}}>
          <Link className="pill" href="/allprojects">View all projects</Link>
        </div>
      </Section>
    </>
  );
}
