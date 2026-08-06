"use client";

export function ShinyText({
  text,
  speed = 4,
  className = "",
}: {
  text: string;
  speed?: number;
  className?: string;
}) {
  return (
    <span
      className={`shiny-text ${className}`}
      style={{ ["--shine-duration" as string]: `${speed}s` }}
    >
      {text}
    </span>
  );
}

export default ShinyText;
