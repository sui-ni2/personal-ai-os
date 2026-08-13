# Product roadmap

Personal AI OS is currently an early V0.2 prototype. The goal is simple by
default and powerful when needed: an ordinary user should be able to configure
the app and complete a natural conversation within a few minutes.

## Priorities

1. **Lock the product and delivery contract**
   - Keep one core with community/self-hosted and managed cloud delivery modes.
   - Use ordinary-language defaults and keep engineering controls in Advanced Settings.
   - Preserve tenant ownership, capabilities, and plan boundaries in every new feature.
2. **Close the first-use loop**
   - Add first-run guidance, provider setup, connection checks, and model lists
     based on configured services.
   - Keep one provider-independent chat interface and make text chat reliable.
3. **Build one Settings center**
   - Bring providers, default models, voice, memory and privacy, appearance,
     language, data controls, MCP, and diagnostics into one coherent place.
4. **Simplify the workspace**
   - Keep Chat, New chat, Model, Projects, and Settings in the default experience.
   - Move Memory, MCP, provider status, logs, and repository controls into an
     advanced or developer mode.
5. **Complete projects, files, outcomes, and reviewed memory**
   - Make Tasks, Conversations, Files, Outcomes, and Project Memory first-class project areas.
   - Save useful results as versioned outcomes without silently writing long-term memory.
6. **Add recovery, routing, privacy, and cost controls**
   - Add cancellation, retry, interrupted-stream recovery, provider fallback, and draft recovery.
   - Add send-scope receipts, explicit side-effect confirmation, budgets, and usage ledgers.
7. **Complete voice end to end**
   - First deliver push-to-talk, speech-to-text, and text submission.
   - Then add spoken replies, interruption, and continuous conversation, with
     room for browser, local, ann}”Nm¢Gß≤⁄Óù∆≠y–                       <span className="flex items-start gap-3">
                                    <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-control bg-surface-subtle text-text-secondary"><FileText aria-hidden size={16} strokeWidth={1.7} /></span>
                                    <span className="min-w-0 flex-1">
                                      <span className="block text-[15px] font-medium leading-6">{item.summary}</span>
                                      <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-tertiary">
                                        <span>{item.project_id || "General"}</span>
                                        <span aria-hidden>¬∑</span>
                                        <span className="capitalize">{item.event_type.replaceAll("_", " ").replaceAll(".", " ")}</span>
                                        <span aria-hidden>¬∑</span>
                                        <span className="text-success">Recorded</span>
                                      </span>
                                      {artifact && <span className="mt-2 block truncate font-mono text-[11px] text-text-secondary">{artifact.locator}</span>}
                                    </span>
                                  </span>
                                </span>
                                <ChevronDown aria-hidden size={17} className="mt-1 text-text-tertiary transition-transform duration-150 group-open/event:rotate-180" />
                              </span>
                            </summary>
                            <div className="border-t border-line bg-surface-subtle/45 px-4 py-4 sm:pl-[100px] sm:pr-5">
                              {details.length ? <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-xs">{details.map((detail) => <div key={`${detail.label}-${detail.value}`} className="contents"><dt className="font-medium text-text-tertiary">{detail.label}</dt><dd className={`min-w-0 break-words text-text-secondary ${detail.mono ? "font-mono text-[11px]" : ""}`}>{detail.value}</dd></div>)}</dl> : <p className="text-xs leading-5 text-text-secondary">No additional details were recorded for this event.</p>}
                            </div>
                          </details>
                        </li>
                      );
                    })}
                  </ol>
                </section>
              ))}
            </div>
          )}
        </section>
      )}

      {!loading && !error && view === "files" && (
        <section aria-label="Repository files" className="space-y-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="section-title">Saved outcomes</h2>
              <p className="mt-1 text-sm text-text-secondary">{artifacts.length} saved {artifacts.length === 1 ? "item" : "items"}</p>
            </div>
            <details className="group relative">
              <summary className="button-primary cursor-pointer list-none"><Plus aria-hidden size={17} />Add outcome</summary>
              <form onSubmit={create} className="panel-elevated mt-2 grid gap-3 p-4 sm:absolute sm:right-0 sm:z-20 sm:w-[420px]">
                <input className="field" aria-label="Outcome title" placeholder="Outcome title" value={title} onChange={(event) => setTitle(event.target.value)} />
                <input className="field font-mono text-xs" aria-label="Safe locator or note reference" placeholder="Safe locator or note reference" value={locator} onChange={(event) => setLocator(event.target.value)} />
                <button className="button-primary" disabled={!title || !locator}>Save outcome</button>
              </form>
            </details>
          </div>
          {artifacts.length === 0 ? (
            <EmptyState title="No saved outcomes" description="Save a useful result or add a note reference when you want to keep it." />
          ) : (
            <div className="overflow-hidden rounded-card border border-line bg-surface">
              {artifacts.map((item) => (
                <article key={item.id} className="flex min-h-16 items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 sm:px-5">
                  <span className="grid size-9 shrink-0 place-items-center rounded-control bg-surface-subtle text-text-secondary"><FolderOpen aria-hidden size={17} strokeWidth={1.7} /></span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    <p className="mt-0.5 truncate font-mono text-[11px] text-text-tertiary">{item.locator}</p>
                  </div>
                  <span className="chip hidden capitalize sm:inline-flex">{item.kind}</span>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
