import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Custom Home Building & Luxury Remodels | Ridgecrest Designs",
  description: "Ridgecrest Designs offers full-service design-build solutions for luxury custom homes and large-scale remodels in the Tri-Valley. Exceptional craftsmanship from concept to completion.",
  alternates: { canonical: "/services" },
};

export default function Services() {
  return (
    <>
      <Section>
        <div className="grid2">
          <div>
            <div className="kicker">Services</div>
            <h1>{site.services.introTitle}</h1>
            <p>{site.services.introBody}</p>
          </div>
          <div className="card">
            <img className="img" src={site.images.servicesBoard} alt="Materials and finish inspiration" />
          </div>
        </div>
      </Section>

      <Section>
        <div className="projGrid">
          {site.services.sections.map((sec) => (
            <div key={sec.title} className="card projB">
              <div className="cardPad">
                <div className="kicker">{sec.title}</div>
                <p style={{marginTop:10}}>{sec.body}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
