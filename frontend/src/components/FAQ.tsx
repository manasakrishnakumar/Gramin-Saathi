import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "Is this service free to use?",
    answer: "Yes, Gramin Saathi is completely free for all rural communities. We believe access to information should be available to everyone.",
  },
  {
    question: "Which languages are supported?",
    answer: "We support 15+ Indian languages including Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and more. You can switch languages anytime.",
  },
  {
    question: "How accurate is the information provided?",
    answer: "Our AI is trained on verified government sources and updated regularly. For critical decisions, we always recommend confirming with local officials.",
  },
  {
    question: "Can I use this without internet?",
    answer: "Currently, an internet connection is required. We're working on an SMS-based service for areas with limited connectivity.",
  },
  {
    question: "How do I report incorrect information?",
    answer: "You can use the feedback option in the chatbot or contact our support team. We review all reports and update our system promptly.",
  },
];

export const FAQ = () => {
  return (
    <section id="faq" className="py-24 bg-muted/30">
      <div className="container mx-auto px-6">
        <div className="text-center space-y-4 mb-16 animate-fade-in">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            FAQ
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Got questions? We've got answers.
          </p>
        </div>

        <div className="max-w-3xl mx-auto">
          <Accordion type="single" collapsible className="space-y-4">
            {faqs.map((faq, index) => (
              <AccordionItem
                key={index}
                value={`item-${index}`}
                className="border-2 border-border rounded-xl px-6 bg-card hover:border-primary/20 transition-colors"
              >
                <AccordionTrigger className="text-left font-semibold hover:text-primary">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground leading-relaxed">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
};
