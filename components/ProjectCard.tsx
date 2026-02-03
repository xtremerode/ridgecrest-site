import Link from "next/link";
export function ProjectCard({title, summary, image, href, size="B"}:{title:string; summary:string; image:string; href:string; size?:"A"|"B";}){
  return (
    <article className={"card " + (size==="A" ? "projA" : "projB")}>
      <Link href={href}>
        <img className="img" src={image} alt={title} loading="lazy" />
        <div className="cardPad">
          <div className="kicker">View project</div>
          <h2 style={{marginTop:10}}>{title}</h2>
          <p>{summary}</p>
        </div>
      </Link>
    </article>
  );
}
