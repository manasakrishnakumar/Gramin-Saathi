import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Hero } from "@/components/Hero";
import { Features } from "@/components/Features";
import { UseCases } from "@/components/UseCases";
import { Testimonials } from "@/components/Testimonials";
import { FAQ } from "@/components/FAQ";
import { Footer } from "@/components/Footer";
import { useNavigate } from "react-router-dom";
// remove Chatbot import
import { ChatbotTrigger } from "@/components/ChatbotTrigger";
import { ParticlesBackground } from "@/components/ParticlesBackground";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background relative">
      <ParticlesBackground className="fixed inset-0 z-0 pointer-events-none" />
      <div className="relative z-10">
        <Navbar />
        <Hero onChatOpen={() => navigate("/chat")} />
        <Features />
        <UseCases />
        <Testimonials />
        <FAQ />
        <Footer />

        <ChatbotTrigger onClick={() => navigate("/chat")} />
      </div>
    </div>
  );
};

export default Index;
