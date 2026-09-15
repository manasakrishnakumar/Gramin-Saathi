import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/clerk-react";
import { LanguageProvider } from "@/contexts/LanguageContext";
import Index from "./pages/Index";
import ChatPage from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import RecommendPage from "./pages/RecommendPage";
import { StatsDashboard } from "./pages/StatsDashboard";
import NotFound from "./pages/NotFound";

import { Navbar } from "@/components/layout/Navbar";

const queryClient = new QueryClient();

import { ThemeProvider } from "@/components/theme-provider"

// ...

const App = () => (
  <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Navbar />
            <div className="pt-16"> {/* Add padding for fixed navbar */}
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/recommend" element={<RecommendPage />} />
                <Route path="/stats" element={<StatsDashboard />} />
                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </div>
          </BrowserRouter>
        </TooltipProvider>
      </LanguageProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
