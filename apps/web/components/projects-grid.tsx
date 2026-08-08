"use client";

import { useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

type Project = { id: string; name: string; description: string; icon: string; status: string };

export function ProjectsGrid() {
  const [items, setItems] = useState<Project[]>([]);
  useEffect(() => { void apiJson<{ items: Project[] }>("/api/projects").then((data) => setItems(data.items)); }, []);
  return <div className="grid gap-4 sm:grid-cols-2">{items.map((item) => <article key={item.id} className="panel p-6"><div className="grid size-12 place-items-center rounded-2xl bg-accent/10 text-xl text-accent">{item.icon === "ball" ? "○" : "✦"}</div><p className="eyebrow mt-7">{item.status} · plugin</p><h2 className="mt-2 text-2xl font-semibold">{item.name}</h2><p className="mt-3 text-sm leading-6 text-muted">{item.description}</p><p className="mt-6 rounded-2xl bg-black/[0.025] p-4 text-xs leading-5 text-muted">Registers context, tools, views, artifacts, and permissions through the same core contract.</p></article>)}</div>;
}
