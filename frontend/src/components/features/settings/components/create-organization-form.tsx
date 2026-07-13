"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Building2 } from "lucide-react";

interface CreateOrganizationFormProps {
  onCreate: (name: string, slug: string, description: string) => void;
  creating: boolean;
  t: Function;
  tc: Function;
}

export default function CreateOrganizationForm({
  onCreate,
  creating,
  t,
  tc,
}: CreateOrganizationFormProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          {t("createOrganization")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("noOrgDescription")}
        </p>
      </div>

      <div className="space-y-4 max-w-md">
        <div className="space-y-2">
          <label htmlFor="newOrgName" className="text-sm font-medium">
            {t("orgName")}
          </label>
          <Input
            id="newOrgName"
            placeholder={t("orgNamePlaceholder")}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slug) {
                setSlug(
                  e.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, "-")
                    .replace(/^-|-$/g, "")
                );
              }
            }}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="newOrgSlug" className="text-sm font-medium">
            {t("slug")}
          </label>
          <Input
            id="newOrgSlug"
            placeholder={t("slugPlaceholder")}
            value={slug}
            onChange={(e) =>
              setSlug(
                e.target.value
                  .toLowerCase()
                  .replace(/[^a-z0-9-]/g, "")
                  .replace(/--+/g, "-")
              )
            }
          />
          <p className="text-xs text-muted-foreground">
            {t("slugHelp")}
          </p>
        </div>
        <div className="space-y-2">
          <label htmlFor="newOrgDescription" className="text-sm font-medium">
            {t("orgDescription")} <span className="text-muted-foreground">{tc("optional")}</span>
          </label>
          <Input
            id="newOrgDescription"
            placeholder={t("orgDescriptionPlaceholder")}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <Button
          onClick={() => onCreate(name.trim(), slug.trim(), description.trim())}
          disabled={creating || !name.trim() || !slug.trim()}
        >
          {creating ? t("creating") : t("createOrganization")}
        </Button>
      </div>
    </div>
  );
}
