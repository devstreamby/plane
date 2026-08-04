/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import Link from "next/link";
import { Controller, useForm } from "react-hook-form";
import { InstanceService } from "@plane/services";
import { Button, getButtonStyling } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceLdapAuthenticationConfigurationKeys } from "@plane/types";
import { TextArea, ToggleSwitch } from "@plane/ui";
import { ConfirmDiscardModal } from "@/components/common/confirm-discard-modal";
import { ControllerInput } from "@/components/common/controller-input";
import { useInstance } from "@/hooks/store";

type Props = {
  config: IFormattedInstanceConfiguration;
};

type LdapConfigFormValues = Record<TInstanceLdapAuthenticationConfigurationKeys, string>;

const instanceService = new InstanceService();

export function InstanceLdapConfigForm({ config }: Props) {
  const [isDiscardChangesModalOpen, setIsDiscardChangesModalOpen] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const { updateInstanceConfigurations } = useInstance();
  const {
    handleSubmit,
    control,
    getValues,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<LdapConfigFormValues>({
    defaultValues: {
      LDAP_PROVIDER_NAME: config.LDAP_PROVIDER_NAME || "Active Directory",
      LDAP_SERVER: config.LDAP_SERVER || "",
      LDAP_PORT: config.LDAP_PORT || "636",
      LDAP_BIND_DN: config.LDAP_BIND_DN || "",
      LDAP_BIND_PASSWORD: config.LDAP_BIND_PASSWORD || "",
      LDAP_USER_SEARCH_BASE: config.LDAP_USER_SEARCH_BASE || "",
      LDAP_USER_SEARCH_FILTER:
        config.LDAP_USER_SEARCH_FILTER ||
        "(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))",
      LDAP_EMAIL_ATTRIBUTE: config.LDAP_EMAIL_ATTRIBUTE || "mail",
      LDAP_FIRST_NAME_ATTRIBUTE: config.LDAP_FIRST_NAME_ATTRIBUTE || "givenName",
      LDAP_LAST_NAME_ATTRIBUTE: config.LDAP_LAST_NAME_ATTRIBUTE || "sn",
      LDAP_CA_CERTIFICATE: config.LDAP_CA_CERTIFICATE || "",
      ENABLE_LDAP_SYNC: config.ENABLE_LDAP_SYNC || "1",
      LDAP_CREATE_USERS: config.LDAP_CREATE_USERS || "1",
    },
  });

  const onSubmit = async (formData: LdapConfigFormValues) => {
    try {
      const response = await updateInstanceConfigurations(formData);
      const nextValues = { ...formData };
      for (const item of response) {
        if (item.key in nextValues) nextValues[item.key as TInstanceLdapAuthenticationConfigurationKeys] = item.value;
      }
      reset(nextValues);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Configuration saved",
        message: "Active Directory settings were saved successfully.",
      });
    } catch (_error) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Save failed", message: "Could not save Active Directory settings." });
    }
  };

  const testConnection = async () => {
    setIsTesting(true);
    try {
      const response = await instanceService.testLdapConnection(getValues());
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Connection succeeded", message: response.message });
    } catch (error) {
      const message =
        typeof error === "object" && error && "error" in error
          ? String(error.error)
          : "Could not connect to Active Directory.";
      setToast({ type: TOAST_TYPE.ERROR, title: "Connection failed", message });
    } finally {
      setIsTesting(false);
    }
  };

  const handleGoBack = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (isDirty) {
      event.preventDefault();
      setIsDiscardChangesModalOpen(true);
    }
  };

  return (
    <>
      <ConfirmDiscardModal
        isOpen={isDiscardChangesModalOpen}
        onDiscardHref="/authentication"
        handleClose={() => setIsDiscardChangesModalOpen(false)}
      />
      <div className="grid w-full grid-cols-2 gap-x-12 gap-y-8">
        <div className="col-span-2 flex flex-col gap-y-4 md:col-span-1">
          <ControllerInput
            control={control}
            type="text"
            name="LDAP_PROVIDER_NAME"
            label="Provider name"
            description="Shown to members on the sign-in screen."
            placeholder="Active Directory"
            error={Boolean(errors.LDAP_PROVIDER_NAME)}
            required
          />
          <div className="grid grid-cols-[1fr_7rem] gap-3">
            <ControllerInput
              control={control}
              type="text"
              name="LDAP_SERVER"
              label="Server"
              description="Hostname or IP address only. Plane always uses LDAPS."
              placeholder="dc01.example.local"
              error={Boolean(errors.LDAP_SERVER)}
              required
            />
            <ControllerInput
              control={control}
              type="text"
              name="LDAP_PORT"
              label="Port"
              placeholder="636"
              error={Boolean(errors.LDAP_PORT)}
              required
            />
          </div>
          <ControllerInput
            control={control}
            type="text"
            name="LDAP_BIND_DN"
            label="Bind account"
            description="A read-only service account in UPN or distinguished-name format."
            placeholder="plane-bind@example.local"
            error={Boolean(errors.LDAP_BIND_DN)}
            required
          />
          <ControllerInput
            control={control}
            type="password"
            name="LDAP_BIND_PASSWORD"
            label="Bind password"
            description="Stored encrypted by Plane."
            placeholder="Enter the service account password"
            error={Boolean(errors.LDAP_BIND_PASSWORD)}
            required
          />
          <ControllerInput
            control={control}
            type="text"
            name="LDAP_USER_SEARCH_BASE"
            label="User search base"
            placeholder="OU=Users,DC=example,DC=local"
            error={Boolean(errors.LDAP_USER_SEARCH_BASE)}
            required
          />
          <ControllerInput
            control={control}
            type="text"
            name="LDAP_USER_SEARCH_FILTER"
            label="User search filter"
            description="Keep {username} in the filter; Plane escapes the supplied value."
            placeholder="(&(objectClass=user)(sAMAccountName={username}))"
            error={Boolean(errors.LDAP_USER_SEARCH_FILTER)}
            required
          />
          <div className="grid grid-cols-3 gap-3">
            <ControllerInput
              control={control}
              type="text"
              name="LDAP_EMAIL_ATTRIBUTE"
              label="Email attribute"
              placeholder="mail"
              error={Boolean(errors.LDAP_EMAIL_ATTRIBUTE)}
              required
            />
            <ControllerInput
              control={control}
              type="text"
              name="LDAP_FIRST_NAME_ATTRIBUTE"
              label="First name"
              placeholder="givenName"
              error={Boolean(errors.LDAP_FIRST_NAME_ATTRIBUTE)}
              required
            />
            <ControllerInput
              control={control}
              type="text"
              name="LDAP_LAST_NAME_ATTRIBUTE"
              label="Last name"
              placeholder="sn"
              error={Boolean(errors.LDAP_LAST_NAME_ATTRIBUTE)}
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-13 text-tertiary">Internal CA certificate</div>
            <Controller
              control={control}
              name="LDAP_CA_CERTIFICATE"
              render={({ field }) => (
                <TextArea
                  {...field}
                  rows={5}
                  placeholder="-----BEGIN CERTIFICATE-----"
                  className="font-mono min-h-28 text-11"
                />
              )}
            />
            <p className="text-11 text-tertiary">
              Leave empty when the issuing CA is already trusted by the API container.
            </p>
          </div>
          <ConfigSwitch
            control={control}
            name="ENABLE_LDAP_SYNC"
            label="Refresh names and email from Active Directory on every sign-in"
          />
          <ConfigSwitch
            control={control}
            name="LDAP_CREATE_USERS"
            label="Create Plane users after their first successful directory sign-in"
          />
          <div className="flex items-center gap-3 pt-4">
            <Button
              variant="primary"
              size="lg"
              onClick={(event) => void handleSubmit(onSubmit)(event)}
              loading={isSubmitting}
              disabled={!isDirty}
            >
              Save changes
            </Button>
            <Button variant="secondary" size="lg" onClick={() => void testConnection()} loading={isTesting}>
              Test connection
            </Button>
            <Link href="/authentication" className={getButtonStyling("secondary", "lg")} onClick={handleGoBack}>
              Go back
            </Link>
          </div>
        </div>
        <div className="col-span-2 md:col-span-1">
          <div className="flex flex-col gap-3 rounded-lg bg-layer-3 px-6 py-5 text-13 text-secondary">
            <div className="text-18 font-medium text-primary">Active Directory requirements</div>
            <p>Use a dedicated read-only bind account and allow the Plane API container to reach TCP port 636.</p>
            <p>The domain controller certificate must match the configured hostname and chain to a trusted CA.</p>
            <p>
              The search result must contain objectGUID and a valid email attribute. Exactly one directory entry must
              match.
            </p>
            <p>Domain passwords are used only for the user bind and are never stored in Plane.</p>
          </div>
        </div>
      </div>
    </>
  );
}

function ConfigSwitch({
  control,
  name,
  label,
}: {
  control: ReturnType<typeof useForm<LdapConfigFormValues>>["control"];
  name: "ENABLE_LDAP_SYNC" | "LDAP_CREATE_USERS";
  label: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-13 text-tertiary">{label}</span>
      <Controller
        control={control}
        name={name}
        render={({ field }) => {
          const enabled = field.value === "1";
          return <ToggleSwitch value={enabled} onChange={() => field.onChange(enabled ? "0" : "1")} size="sm" />;
        }}
      />
    </div>
  );
}
