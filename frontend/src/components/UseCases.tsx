import { Card } from "@/components/ui/card";
import { Wheat, GraduationCap, Building2, Users2, Briefcase } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const useCases = [
  {
    icon: Wheat,
    title: "Farmers",
    description: "Access crop advisories, weather forecasts, market prices, and agricultural scheme information.",
    color: "from-emerald-500 to-green-600",
  },
  {
    icon: GraduationCap,
    title: "Rural Students",
    description: "Get information on scholarships, educational programs, and career guidance opportunities.",
    color: "from-blue-500 to-indigo-600",
  },
  {
    icon: Building2,
    title: "Village Officials",
    description: "Help constituents find information and navigate government services efficiently.",
    color: "from-purple-500 to-pink-600",
  },
  {
    icon: Users2,
    title: "SHG Groups",
    description: "Learn about microfinance, training programs, and women empowerment schemes.",
    color: "from-orange-500 to-red-600",
  },
  {
    icon: Briefcase,
    title: "Rural Entrepreneurs",
    description: "Discover business support schemes, loan programs, and skill development initiatives.",
    color: "from-cyan-500 to-blue-600",
  },
];

export const UseCases = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.1 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, []);

  return (
    <section id="use-cases" className="py-24 bg-transparent">
      <style>{`
        @keyframes popInReveal {
          0% {
            opacity: 0;
            transform: translate3d(0, 20px, 0) scale(0.85);
          }
          50% {
            opacity: 1;
          }
          100% {
            opacity: 1;
            transform: translate3d(0, 0, 0) scale(1);
          }
        }

        @keyframes glowPulse {
          0% {
            box-shadow: 0 0 30px rgba(45, 80, 22, 0.6), 0 0 60px rgba(74, 144, 226, 0.4);
          }
          100% {
            box-shadow: 0 0 0px rgba(45, 80, 22, 0), 0 0 0px rgba(74, 144, 226, 0);
          }
        }

        @keyframes iconPop {
          0% {
            opacity: 0;
            transform: scale(0.6) rotate(-10deg);
          }
          100% {
            opacity: 1;
            transform: scale(1) rotate(0deg);
          }
        }

        @keyframes bloom {
          0% {
            transform: scale(0.5);
            opacity: 0.4;
          }
          100% {
            transform: scale(1.5);
            opacity: 0;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .reveal-card-premium {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
          }
          
          .card-bloom {
            animation: none !important;
          }
          
          .card-icon {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
          }
        }

        .reveal-card-premium {
          opacity: 0;
          animation: popInReveal 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
          will-change: transform, opacity;
        }

        .reveal-card-premium.is-visible {
          opacity: 1;
        }

        .card-glow {
          animation: glowPulse 0.4s ease-out forwards;
        }

        .card-bloom {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 100%;
          height: 100%;
          pointer-events: none;
        }

        .bloom-effect {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(45, 80, 22, 0.3), transparent);
          animation: bloom 0.8s ease-out forwards;
        }

        .card-icon {
          opacity: 0;
          animation: iconPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
          will-change: transform;
        }
      `}</style>

      <div className="container mx-auto px-6">
        <div className="text-center space-y-4 mb-16 animate-fade-in">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            Use Cases
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold">
            Built for Everyone in Rural India
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Whether you're farming, studying, or building a business, Gramin Saathi is here to help.
          </p>
        </div>

        {/* Horizontal Single Row Container - No Scroll */}
        <div className="relative overflow-hidden">
          <div 
            ref={containerRef} 
            className="flex gap-4 md:gap-5 justify-center flex-wrap"
          >
            {useCases.map((useCase, index) => (
              <Card
                key={index}
                className="flex-shrink-0 w-56 md:w-60 h-auto p-6 hover:shadow-xl transition-all duration-300 border-2 hover:border-primary/20 bg-card group overflow-hidden relative reveal-card-premium"
                style={{
                  animationDelay: isVisible ? `${index * 0.15}s` : "0s",
                }}
              >
                {/* Glow effect on reveal */}
                <div 
                  className={`absolute inset-0 rounded-lg card-glow ${isVisible ? 'card-glow' : ''}`}
                  style={{
                    animationDelay: isVisible ? `${index * 0.15}s` : "0s",
                  }}
                />

                {/* Bloom effect */}
                {isVisible && (
                  <div 
                    className="card-bloom"
                    style={{
                      animationDelay: isVisible ? `${index * 0.15}s` : "0s",
                    }}
                  >
                    <div className="bloom-effect" />
                  </div>
                )}

                {/* Background gradient accent */}
                <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${useCase.color} opacity-10 rounded-full blur-3xl group-hover:opacity-20 transition-opacity -z-0`} />
                
                <div className="relative z-10">
                  {/* Icon with separate animation */}
                  <div 
                    className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${useCase.color} flex items-center justify-center mb-6 card-icon`}
                    style={{
                      animationDelay: isVisible ? `${index * 0.15 + 0.1}s` : "0s",
                    }}
                  >
                    <useCase.icon className="w-7 h-7 text-white" />
                  </div>

                  <h3 className="text-xl font-bold mb-3 group-hover:text-primary transition-colors">
                    {useCase.title}
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {useCase.description}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
