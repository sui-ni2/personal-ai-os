import { Fragment, type ReactNode } from "react";

function inlineContent(text: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index} className="rounded-small bg-surface-subtle px-1.5 py-0.5 font-mono text-[0.9em] text-text-primary">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index} className="font-medium text-text-primary">{part.slice(2, -2)}</strong>;
    }
    return <Fragment key={index}>{part}</Fragment>;
  });
}

function tableCells(line: string) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

export function RichMessage({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.trim().startsWith("```")) {
      const language = line.trim().slice(3).trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push(
        <div key={`code-${index}`} className="my-4 overflow-hidden rounded-control border border-line bg-text-primary text-surface">
          {language && <div className="border-b border-surface/15 px-4 py-2 font-mono text-[11px] text-surface/65">{language}</div>}
          <pre className="scrollbar-subtle max-h-[420px] overflow-auto p-4 font-mono text-xs leading-6"><code>{code.join("\n")}</code></pre>
        </div>,
      );
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const className = heading[1].length === 1 ? "mt-6 text-xl" : heading[1].length === 2 ? "mt-5 text-lg" : "mt-4 text-base";
      blocks.push(<h3 key={`heading-${index}`} className={`${className} mb-2 font-medium tracking-[-0.015em]`}>{inlineContent(heading[2])}</h3>);
      index += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(<ul key={`list-${index}`} className="my-3 list-disc space-y-1.5 pl-5">{items.map((item, itemIndex) => <li key={itemIndex}>{inlineContent(item)}</li>)}</ul>);
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+[.)]\s+/, ""));
        index += 1;
      }
      blocks.push(<ol key={`ordered-${index}`} className="my-3 list-decimal space-y-1.5 pl-5">{items.map((item, itemIndex) => <li key={itemIndex}>{inlineContent(item)}</li>)}</ol>);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push(<blockquote key={`quote-${index}`} className="my-4 border-l-2 border-accent pl-4 text-text-secondary">{inlineContent(quote.join(" "))}</blockquote>);
      continue;
    }

    if (line.includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-+/.test(lines[index + 1])) {
      const headers = tableCells(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|")) {
        rows.push(tableCells(lines[index]));
        index += 1;
      }
      blocks.push(
        <div key={`table-${index}`} className="scrollbar-subtle my-4 overflow-x-auto rounded-control border border-line">
          <table className="w-full min-w-[420px] border-collapse text-left text-sm">
            <thead className="bg-surface-subtle"><tr>{headers.map((header, cellIndex) => <th key={cellIndex} className="border-b border-line px-3 py-2 font-medium">{inlineContent(header)}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex} className="border-b border-line last:border-b-0">{row.map((cell, cellIndex) => <td key={cellIndex} className="px-3 py-2 text-text-secondary">{inlineContent(cell)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,3})\s+/.test(lines[index]) &&
      !/^\s*[-*]\s+/.test(lines[index]) &&
      !/^\s*\d+[.)]\s+/.test(lines[index]) &&
      !/^\s*>\s?/.test(lines[index]) &&
      !lines[index].trim().startsWith("```")
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(<p key={`paragraph-${index}`} className="my-2 leading-7">{inlineContent(paragraph.join(" "))}</p>);
  }

  return <div className="min-w-0">{blocks}</div>;
}
