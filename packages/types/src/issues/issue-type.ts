/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "../common";

export type TIssueType = {
  readonly id: string;
  workspace_id: string;
  name: string;
  description: string;
  logo_props: TLogoProps;
  is_active: boolean;
  is_epic: boolean;
  is_default: boolean;
  level: number;
};

export type TIssueTypePayload = {
  name?: string;
  description?: string;
  logo_props?: TLogoProps;
  is_active?: boolean;
};
