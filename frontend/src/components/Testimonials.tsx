import { Card } from "@/components/ui/card";
import { Star } from "lucide-react";

const testimonials = [
  {
    name: "Rajesh Kumar",
    role: "Farmer, Maharashtra",
    content: "This chatbot helped me understand the PM-KISAN scheme in minutes. I got my application approved within a week. Amazing support!",
    rating: 5,
    avatar: "👨‍🌾",
  },
  {
    name: "Priya Sharma",
    role: "SHG Leader, Rajasthan",
    content: "Our women's group uses this daily to find information about various government schemes. It's like having an expert always available.",
    rating: 5,
    avatar: "👩",
  },
  {
    name: "Suresh Patel",
    role: "Student, Gujarat",
    content: "Found scholarship information I never knew existed. The multilingual support in Gujarati made it so easy to understand everything.",
    rating: 5,
    avatar: "👨‍🎓",
  },
];

export const Testimonials = () => {
  return (
    <section className="py-24">
      <div className="container mx-auto px-6">
        <div className="text-center space-y-4 mb-16 animate-fade-in">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-accent/10 text-accent text-sm font-medium">
            Testimonials
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold">
            Trusted by Communities Across India
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Real stories from real people who found the help they needed.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <Card
              key={index}
              className="p-8 hover:shadow-xl transition-all duration-300 border-2 hover:border-primary/20 bg-card animate-fade-in"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="flex items-center gap-1 mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 fill-accent text-accent" />
                ))}
              </div>
              
              <p className="text-muted-foreground leading-relaxed mb-6">
                "{testimonial.content}"
              </p>

              <div className="flex items-center gap-3 pt-4 border-t border-border">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-2xl">
                  {testimonial.avatar}
                </div>
                <div>
                  <div className="font-semibold">{testimonial.name}</div>
                  <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};
