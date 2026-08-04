/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { Settings2 } from "lucide-react";
import { getButtonStyling } from "@plane/propel/button";
import type { TInstanceAuthenticationMethodKeys } from "@plane/types";
import { ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
import { useInstance } from "@/hooks/store";

type Props = {
  disabled: boolean;
  updateConfig: (key: TInstanceAuthenticationMethodKeys, value: string) => void;
};

export const LdapConfiguration = observer(function LdapConfiguration(props: Props) {
  const { disabled, updateConfig } = props;
  const { formattedConfig } = useInstance();
  const enabled = formattedConfig?.IS_LDAP_ENABLED ?? "0";
  const isConfigured =
    !!formattedConfig?.LDAP_SERVER && !!formattedConfig?.LDAP_BIND_DN && !!formattedConfig?.LDAP_USER_SEARCH_BASE;

  if (!isConfigured) {
    return (
      <Link href="/authentication/ldap" className={cn(getButtonStyling("secondary", "base"), "text-tertiary")}>
        <Settings2 className="h-4 w-4 p-0.5 text-tertiary" />
        Configure
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-4">
      <Link href="/authentication/ldap" className={cn(getButtonStyling("link", "base"), "font-medium")}>
        Edit
      </Link>
      <ToggleSwitch
        value={Boolean(parseInt(enabled))}
        onChange={() => updateConfig("IS_LDAP_ENABLED", parseInt(enabled) ? "0" : "1")}
        size="sm"
        disabled={disabled}
      />
    </div>
  );
});
