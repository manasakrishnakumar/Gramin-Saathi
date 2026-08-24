"use client";

import { CheckCircle2, FileText, BookOpen, HelpCircle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface FeedbackFormDisplayProps {
  success: boolean;
  message: string;
  form?: {
    id: string;
    title: string;
    course_code: string;
    question_count: number;
  };
  error?: string;
}

export function FeedbackFormDisplay({ success, message, form, error }: FeedbackFormDisplayProps) {
  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!success) {
    return (
      <div className="p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800">
        <p className="text-sm text-yellow-600 dark:text-yellow-400">{message}</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/20 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-1">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="space-y-1">
          <h3 className="font-medium text-emerald-900 dark:text-emerald-100">
            Feedback Form Created
          </h3>
          <p className="text-sm text-emerald-700 dark:text-emerald-300">
            {message}
          </p>
        </div>
      </div>

      {form && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex items-center gap-2 p-2 rounded bg-white/50 dark:bg-black/20 border border-emerald-100 dark:border-emerald-800/50">
            <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <div className="text-xs">
              <p className="text-emerald-600/70 dark:text-emerald-400/70 font-medium">Title</p>
              <p className="text-emerald-900 dark:text-emerald-100 font-semibold truncate max-w-[120px]" title={form.title}>
                {form.title}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 rounded bg-white/50 dark:bg-black/20 border border-emerald-100 dark:border-emerald-800/50">
            <BookOpen className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <div className="text-xs">
              <p className="text-emerald-600/70 dark:text-emerald-400/70 font-medium">Course</p>
              <p className="text-emerald-900 dark:text-emerald-100 font-semibold">
                {form.course_code}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 rounded bg-white/50 dark:bg-black/20 border border-emerald-100 dark:border-emerald-800/50">
            <HelpCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <div className="text-xs">
              <p className="text-emerald-600/70 dark:text-emerald-400/70 font-medium">Questions</p>
              <p className="text-emerald-900 dark:text-emerald-100 font-semibold">
                {form.question_count}
              </p>
            </div>
          </div>
        </div>
      )}

      {form && (
        <div className="mt-4 flex justify-end">
          <Link href={`/faculty/feedback/${form.id}`} passHref>
            <Button 
              variant="outline" 
              size="sm" 
              className="bg-white/50 dark:bg-black/20 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
            >
              View Form
              <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
