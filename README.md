# StockQuery AI 📦🤖

<div align="center">
  <img src="public/logo.svg" alt="StockQuery AI Logo" width="120" />
</div>

<p align="center">
  <strong>Inventory Intelligence and AI-powered Querying</strong>
</p>

## Overview
StockQuery AI is a modern, premium web application built to streamline inventory management using a beautifully designed visual interface and data-driven intelligence. Built with React and structured with highly customizable UI components, it enables businesses to monitor dashboard metrics, chat iteratively regarding stock questions, establish smart threshold alerts, and easily manage product catalogs.

## 🌟 Features
- **Secure Authentication**: Integrated with Firebase Authentication, supporting both Email/Password registrations and centralized Google OAuth SSO.
- **Dynamic Dashboard**: Responsive grid layouts featuring interactive bar and pie charts representing live inventory value distributions (powered by Recharts).
- **Intelligent Sidebar**: Retractable side navigation displaying context-aware user profile cards and intuitive routing.
- **Agentic AI Chat Interface** *(UI Layer)*: A chat interface layout primed and ready for backend LLM tool integration to answer your inventory queries naturally.
- **Premium Design System**: Complete adoption of Tailwind CSS and "Glassmorphism" design philosophies including micro-interactions, dark/light mode optimization, animated sliding frames, and custom typography frameworks utilizing Shadcn UI & Radix.

## 🛠️ Tech Stack
- **Frontend Framework**: React 18 / Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS + `lucide-react` (iconography)
- **Component Library**: shadcn/ui + Radix Primitives
- **Routing**: `react-router-dom`
- **Authentication**: Firebase Auth (v12)
- **Data Visualization**: Recharts

## 🚀 Getting Started

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) installed on your machine. 

### Installation
1. Setup the workspace and install the dependencies:
```bash
npm install
```

2. Fire up the local development server:
```bash
npm run dev
```

3. Open your browser and navigate to the address shown in the terminal (usually `http://localhost:8080/` or `http://localhost:8081/`).

### Building for Production
To create an optimized production build of the client application:
```bash
npm run build
```

## 🔐 Firebase Configuration
Authentication depends on a connected Firebase Project. To customize it for your own environment:
1. Navigate to `src/lib/firebase.ts`.
2. Replace the `firebaseConfig` object with your project parameters provided by the Firebase Console.
3. Ensure you have actively enabled both **Email/Password** and **Google** sign-in providers in the Firebase Authentication settings tab.

---
*Developed with precision for modern inventory intelligence.*
