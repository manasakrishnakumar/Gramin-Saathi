import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { ModeToggle } from "@/components/mode-toggle";

export function Navbar() {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-md">
            <div className="flex items-center gap-2">
                <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary md:text-2xl transition-transform hover:scale-105">
                    <ShieldCheck className="h-8 w-8" />
                    <span>Gramin Saathi</span>
                </Link>
            </div>

            <div className="flex items-center gap-6">
                <div className="hidden md:flex items-center gap-6 text-sm font-medium">
                    <Link to="/" className="transition-colors hover:text-primary">Home</Link>
                    <Link to="/chat" className="transition-colors hover:text-primary">Chat</Link>
                </div>

                <div className="flex items-center gap-4">
                    <ModeToggle />
                    <SignedOut>
                        <SignInButton mode="modal">
                            <button className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">
                                Sign In
                            </button>
                        </SignInButton>
                    </SignedOut>
                    <SignedIn>
                        <UserButton afterSignOutUrl="/" />
                    </SignedIn>
                </div>
            </div>
        </nav>
    );
}
