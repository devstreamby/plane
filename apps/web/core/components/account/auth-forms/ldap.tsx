/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import { API_BASE_URL } from "@plane/constants";
import { Button } from "@plane/propel/button";
import { Input, Spinner } from "@plane/ui";
import { AuthService } from "@/services/auth.service";

type Props = {
  providerName: string;
  nextPath?: string;
  onBack: () => void;
};

const authService = new AuthService();

export function LdapSignInForm({ providerName, nextPath, onBack }: Props) {
  const formRef = useRef<HTMLFormElement>(null);
  const [csrfPromise, setCsrfPromise] = useState<Promise<{ csrf_token: string }>>();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setCsrfPromise(authService.requestCSRFToken());
  }, []);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = await csrfPromise;
    if (!token?.csrf_token || !formRef.current) return;
    const csrfInput = formRef.current.querySelector<HTMLInputElement>("input[name=csrfmiddlewaretoken]");
    if (csrfInput) csrfInput.value = token.csrf_token;
    setIsSubmitting(true);
    formRef.current.submit();
  };

  return (
    <form
      ref={formRef}
      method="POST"
      action={`${API_BASE_URL}/auth/ldap/`}
      onSubmit={(event) => void submit(event)}
      className="space-y-4"
    >
      <input type="hidden" name="csrfmiddlewaretoken" />
      {nextPath && <input type="hidden" name="next_path" value={nextPath} />}
      <div className="space-y-1">
        <label htmlFor="ldap-username" className="text-13 font-medium text-tertiary">
          Domain username
        </label>
        <Input
          id="ldap-username"
          name="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="username or username@example.local"
          autoComplete="username"
          className="h-10 w-full border border-strong !bg-surface-1"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="ldap-password" className="text-13 font-medium text-tertiary">
          Domain password
        </label>
        <div className="relative">
          <Input
            id="ldap-password"
            name="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={`Password for ${providerName}`}
            autoComplete="current-password"
            className="h-10 w-full border border-strong !bg-surface-1 pr-12"
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            className="absolute top-2.5 right-3 grid size-5 place-items-center"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeOff className="size-5 stroke-placeholder" />
            ) : (
              <Eye className="size-5 stroke-placeholder" />
            )}
          </button>
        </div>
      </div>
      <div className="space-y-2.5">
        <Button
          type="submit"
          variant="primary"
          size="xl"
          className="w-full"
          disabled={!username || !password || isSubmitting}
        >
          {isSubmitting ? <Spinner height="20px" width="20px" /> : `Continue with ${providerName}`}
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="xl"
          className="w-full"
          onClick={onBack}
          prependIcon={<ArrowLeft />}
        >
          Back to other sign-in methods
        </Button>
      </div>
      <p className="text-center text-11 text-tertiary">
        Your domain password is verified by Active Directory and is not stored in Plane.
      </p>
    </form>
  );
}
