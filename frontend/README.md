# Frontend

React frontend for JobDex. Renders the landing page, interactive world map, and job discovery UI.

## Tech Stack

| Layer                 | Choice                        |
| --------------------- | ----------------------------- |
| Framework             | React 19 + Vite               |
| Language              | TypeScript v6                 |
| Styling               | Tailwind CSS v4               |
| Components            | shadcn/ui (base-nova)         |
| UI Extras             | Magic UI (Globe, Highlighter) |
| Map                   | Leaflet + OpenStreetMap       |
| Routing               | React Router v7               |
| Dependency Management | pnpm                          |
| Deployment            | Docker + nginx                |

## Getting Started

### Prerequisites

- Node.js 22+
- pnpm 11+

### Installation

```bash
git clone <repo-url>
cd jobdex/frontend
pnpm install
```

### Running Locally

```bash
pnpm dev
```

Available at `http://localhost:3000`.

## Docker

### Docker Compose

Run from the repository root:

```bash
docker compose up --build
```

### Standalone Container

```bash
cd frontend

docker build -t jobdex-frontend .

docker run -p 3000:80 jobdex-frontend
```
