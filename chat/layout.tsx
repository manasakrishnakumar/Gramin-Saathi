import { createSupabaseServer } from "@/lib/supabase/server";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ConversationsProvider } from "./hooks/conversations-context";
import { AppSidebar } from "./components/sidebar/app-sidebar";
import { getCurrentUser } from "@/lib/supabase/queries/server/auth";
import { redirect } from "next/navigation";

export default async function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createSupabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // const adminuser = await getCurrentUser();
    
  // if (!adminuser) {
  //   redirect("/signin");
  // }

  // if (adminuser.role !== "admin") {
  //   redirect("/");
  // }
  return (
    <div className="flex h-screen">
      <ConversationsProvider userId={user?.id ?? ""}>
        <SidebarProvider defaultOpen={true}>
          <AppSidebar user={user} />
          <div className="flex-1 ">{children}</div>
        </SidebarProvider>
      </ConversationsProvider>
    </div>
  );
}
