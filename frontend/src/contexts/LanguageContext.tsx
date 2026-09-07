import { createContext, useContext, useState, ReactNode, useEffect } from "react";

export type Language = "en" | "hi" | "ta" | "te" | "kn" | "ml" | "gu" | "mr" | "bn" | "pa";

export interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem("language");
    return (saved as Language) || "en";
  });

  useEffect(() => {
    localStorage.setItem("language", language);
  }, [language]);

  // Auto-detect language on mount (if valid detection found)
  useEffect(() => {
    // Only auto-detect when there's no saved preference yet. Without this
    // guard, detection re-runs on every full page load and — if it
    // resolves — unconditionally overwrites whatever language is currently
    // set, silently discarding any saved/explicit choice a few hundred ms
    // after the page loads. That also makes the `localStorage.setItem`
    // effect above pointless: whatever it persisted gets clobbered again
    // on the very next load.
    if (localStorage.getItem("language")) return;

    const initLang = async () => {
      // Dynamic import to avoid cycles/bundling issues if any
      const module = await import("@/services/geolocation");
      const detected = await module.detectLocationAndLanguage();
      if (detected) {
        console.log("Global Language Detection:", detected);
        // We map the full name (e.g. Kannada) to our code (kn) if possible, 
        // but our Language type uses codes ("en", "hi").
        // And STATE_LANGUAGE_MAP returns full names ("Kannada").
        // We need a mapping from Full Name -> Code.

        // Simple reverse map or just update type? 
        // Currently ChatPage and RAG accept "English", "Kannada" strings too?
        // Let's check RAG service. It takes `target_language: str` (Full Name expected).

        // LanguageContext uses 'en' | 'hi' codes.
        // We should align them. 
        // Currently `LANGUAGE_MAP` in ChatPage maps 'en' -> 'English'.
        // If detected is "Kannada", we need to find the key 'kn'.

        const LangMap: Record<string, string> = {
          "English": "en", "Hindi": "hi", "Tamil": "ta", "Telugu": "te", "Kannada": "kn",
          "Malayalam": "ml", "Gujarati": "gu", "Marathi": "mr", "Bengali": "bn", "Punjabi": "pa"
        };

        const code = LangMap[detected] as Language;
        if (code) {
          setLanguageState(code);
        }
      }
    };
    initLang();
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
