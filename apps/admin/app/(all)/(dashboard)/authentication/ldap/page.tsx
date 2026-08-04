/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Network } from "lucide-react";
import useSWR from "swr";
import { setPromiseToast } from "@plane/propel/toast";
import { Loader, ToggleSwitch } from "@plane/ui";
import { AuthenticationMethodCard } from "@/components/authentication/authentication-method-card";
import { PageWrapper } from "@/components/common/page-wrapper";
import { useInstance } from "@/hooks/store";
import type { Route } from "./+types/page";
import { InstanceLdapConfigForm } from "./form";

const InstanceLdapAuthenticationPage = observer(function InstanceLdapAuthenticationPage(_props: Route.ComponentProps) {
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const enabled = formattedConfig?.IS_LDAP_ENABLED ?? "0";

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const updateEnabled = async (value: string) => {
    setIsSubmitting(true);
    const promise = updateInstanceConfigurations({ IS_LDAP_ENABLED: value });
    setPromiseToast(promise, {
      loading: "Saving configuration",
      success: {
        title: "Configuration saved",
        message: () => `Active Directory authentication is now ${value === "1" ? "active" : "disabled"}.`,
      },
      error: { title: "Error", message: () => "Failed to update Active Directory authentication." },
    });
    try {
      await promise;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper
      customHeader={
        <AuthenticationMethodCard
          name="Active Directory"
          description="Allow members to sign in with an on-premises directory account over secure LDAPS."
          icon={<Network className="h-6 w-6 text-tertiary" />}
          config={
            <ToggleSwitch
              value={Boolean(parseInt(enabled))}
              onChange={() => void updateEnabled(parseInt(enabled) ? "0" : "1")}
              size="sm"
              disabled={isSubmitting || !formattedConfig}
            />
          }
          disabled={isSubmitting || !formattedConfig}
          withBorder={false}
        />
      }
    >
      {formattedConfig ? (
        <InstanceLdapConfigForm config={formattedConfig} />
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" />
          <Loader.Item height="50px" />
          <Loader.Item height="50px" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Active Directory Authentication - God Mode" }];

export default InstanceLdapAuthenticationPage;
