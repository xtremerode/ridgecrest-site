import Section from "@/components/Section";
import { site } from "@/data/site";
import { ProjectCard } from "@/components/ProjectCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "All Projects – Ridgecrest Designs",
  description: "A complete gallery of Ridgecrest Designs’ luxury custom design build home and renovation projects.",
  alternates: { canonical: "/allprojects" },
};

export default function AllProjects() {
  const items = site.projects;
  return (
    <>
      <Section>
        <div className="kicker">All Projects</div>
        <h1>All Projects</h1>
        <p>Selected project pages built from your current site content.</p>
      </Section>

      <Section>
        <div className="projGrid">
          {items.map((p, idx) => (
            <ProjectCard
              key={p.slug}
              size={idx===0 ? "A" : "B"}
              title={p.title}
              summary={`${p.what} · ${p.where} · ${p.when}`}
              image={p.hero}
              href={p.slug}
            />
          ))}
        </div>
      </Section>
    </>
  );
}
