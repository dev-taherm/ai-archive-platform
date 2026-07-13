"use client";

import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SearchPaginationProps {
  currentPage: number;
  totalPages: number;
  offset: number;
  maxResults: number;
  onPageChange: (newOffset: number) => void;
}

export function SearchPagination({
  currentPage,
  totalPages,
  offset,
  maxResults,
  onPageChange,
}: SearchPaginationProps) {
  const t = useTranslations("search");
  const tc = useTranslations("common");

  return (
    <div className="flex items-center justify-between pt-2">
      <span className="text-sm text-muted-foreground">
        {t("pageInfo", { current: currentPage, total: totalPages })}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(offset - maxResults)}
          disabled={offset === 0}
        >
          <ChevronLeft className="h-4 w-4" />
          {tc("previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(offset + maxResults)}
          disabled={currentPage >= totalPages}
        >
          {tc("next")}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
