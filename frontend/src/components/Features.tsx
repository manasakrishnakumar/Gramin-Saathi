import { MessageSquare, Sprout, Globe, FileText, Users, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";

const features = [
  {
    icon: MessageSquare,
    title: "Real-time Rural Assistance",
    description: "Get instant answers to your questions about local services, schemes, and community resources 24/7.",
  },
  {
    icon: FileText,
    title: "Government Scheme Guidance",
    description: "Navigate complex government programs with step-by-step guidance on eligibility and application processes.",
  },
  {
    icon: Sprout,
    title: "Agriculture Support Info",
    description: "Access farming techniques, crop management tips, weather updates, and market price information.",
  },
  {
    icon: Users,
    title: "Complaint Submission",
    description: "Report issues and submit complaints to local authorities with guided assistance for proper documentation.",
  },
  {
    icon: Globe,
    title: "Multilingual Support",
    description: "Communicate in your preferred language from 15+ regional languages for seamless understanding.",
  },
  {
    icon: Zap,
    title: "Smart & Fast",
    description: "Powered by advanced AI to provide accurate, contextual responses instantly without any wait time.",
  },
];

const FeatureCard = ({ feature }: { feature: typeof features[0] }) => (
  <Card className="min-w-[320px] md:min-w-[380px] p-8 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-2 border-primary/40 dark:border-primary/30 rounded-2xl shadow-lg transition-all duration-300 group hover:bg-white/95 dark:hover:bg-slate-800/95 hover:border-primary/60">
    <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
      <feature.icon className="w-7 h-7 text-primary" />
    </div>
    <h3 className="text-xl font-bold mb-3 group-hover:text-primary transition-colors line-clamp-2">
      {feature.title}
    </h3>
    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3">
      {feature.description}
    </p>
  </Card>
);

export const Features = () => {
  // Duplicate features for seamless loop
  const duplicatedFeatures = [...features, ...features];

  return (
    <section id="features" className="py-24 bg-transparent relative">
      <style>{`
        @keyframes marquee {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .marquee-track {
            animation: none !important;
          }
        }

        .marquee-track {
          animation: marquee 20s linear infinite;
          will-change: transform;
        }

        .marquee-track:hover {
          animation-play-state: paused;
        }
      `}</style>

      <div className="container mx-auto px-6">
        <div className="text-center space-y-4 mb-16 animate-fade-in">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            Features
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold">
            Everything You Need in One Place
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Comprehensive support designed specifically for rural communities with features that matter most.
          </p>
        </div>
      </div>

      {/* Carousel Container */}
      <div className="relative h-full mt-12 px-6">
        {/* Left Fade Gradient */}
        <div className="absolute left-0 top-0 bottom-0 w-20 md:w-32 bg-gradient-to-r from-background/100 via-background/50 to-transparent z-20 pointer-events-none" />
        
        {/* Right Fade Gradient */}
        <div className="absolute right-0 top-0 bottom-0 w-20 md:w-32 bg-gradient-to-l from-background/100 via-background/50 to-transparent z-20 pointer-events-none" />

        {/* Carousel Track */}
        <div className="overflow-hidden">
          <div className="marquee-track flex gap-6 md:gap-8">
            {duplicatedFeatures.map((feature, index) => (
              <FeatureCard key={index} feature={feature} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};