/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TFilterProperty, TIssueType, TLogoProps, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
// local imports
import { getMultiSelectConfig } from "../../../rich-filters/factories/configs/core";
import type {
  TCreateFilterConfigParams,
  IFilterIconConfig,
  TCreateFilterConfig,
} from "../../../rich-filters/factories/configs/shared";
import { createFilterConfig, createOperatorConfigEntry } from "../../../rich-filters/factories/configs/shared";

/**
 * Work item type filter specific params
 */
export type TCreateWorkItemTypeFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TLogoProps> & {
    workItemTypes: TIssueType[];
    // Required so the caller always supplies a translated label; this package has
    // no access to the i18n runtime.
    label: string;
  };

/**
 * Helper to get the work item type multi select config
 * @param params - The filter params
 * @returns The work item type multi select config
 */
export const getWorkItemTypeMultiSelectConfig = (
  params: TCreateWorkItemTypeFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<TIssueType, string, TLogoProps>(
    {
      items: params.workItemTypes,
      getId: (workItemType) => workItemType.id,
      getLabel: (workItemType) => workItemType.name,
      getValue: (workItemType) => workItemType.id,
      // The icon itself is rendered by the caller's getOptionIcon; this package is
      // React-free, so only the logo data crosses the boundary.
      getIconData: (workItemType) => workItemType.logo_props,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      ...params,
    }
  );

/**
 * Get the work item type filter config
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the work item type filter config
 */
export const getWorkItemTypeFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateWorkItemTypeFilterParams> =>
  (params: TCreateWorkItemTypeFilterParams) =>
    createFilterConfig<P>({
      id: key,
      ...params,
      label: params.label,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getWorkItemTypeMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
