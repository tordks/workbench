---
type: practice
title: React + Vite project setup
aliases: [react-vite-project, react-setup, vite-setup]
tags: [frontend, tooling, testing]
created: 2026-07-02
updated: 2026-07-02
status: draft
related: ["[[python-project]]"]
---

# React + Vite project setup

A setup recipe, not a scaffold. Vite scaffolds the app; this page is *what to run, add, and stand
by*.

## Bootstrap
```
npm create vite@latest <name> -- --template react-ts
cd <name>
npm install
npm install -D vitest @testing-library/react @testing-library/jsdom jsdom msw
```

## Conventions
- **Build tool:** Vite. **Language:** TypeScript throughout.
- **Types:** `tsc --noEmit` as the typecheck gate (`npm run typecheck`).
- **Tests:** `vitest` with the **jsdom** environment; component tests via Testing Library.
- **Network in tests:** **MSW** (Mock Service Worker) — mock at the HTTP boundary, not by stubbing
  modules. Keeps tests honest about the real request/response contract.
- **API types:** generate TS types from the backend's live OpenAPI schema rather than hand-writing
  them (`npm run generate-api-types`); the frontend consumes generated types.
- **Dev server:** `npm run dev`, proxying API calls to the backend.

## Commands cheat-sheet
```
npm test              # vitest (jsdom + MSW)
npm run typecheck     # tsc --noEmit
npm run dev           # local dev server
npm run generate-api-types
```
