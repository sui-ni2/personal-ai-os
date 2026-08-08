export function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="mb-8">
      <p className="eyebrow">{eyebrow}</p>
      <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-0.04em] sm:text-5xl">{title}</h1>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:text-base">{description}</p>
    </header>
  );
}
