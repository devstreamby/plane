/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TBoardColumn, TFilterProperty, TSupportedOperators } from "@plane/types";
import { COLLECTION_OPERATOR, EQUALITY_OPERATOR } from "@plane/types";
// local imports
import type { IFilterIconConfig, TCreateFilterConfig, TCreateFilterConfigParams } from "../../../rich-filters";
import { createFilterConfig, createOperatorConfigEntry, getMultiSelectConfig } from "../../../rich-filters";

export type TCreateBoardColumnFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<undefined> & {
    boardColumns: TBoardColumn[];
    label: string;
  };

export const getBoardColumnMultiSelectConfig = (
  params: TCreateBoardColumnFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<TBoardColumn, string, undefined>(
    {
      items: params.boardColumns,
      getId: (column) => column.id,
      getLabel: (column) => column.name,
      getValue: (column) => column.id,
      getIconData: () => undefined,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      ...params,
    }
  );

export const getBoardColumnFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateBoardColumnFilterParams> =>
  (params: TCreateBoardColumnFilterParams) =>
    createFilterConfig<P>({
      id: key,
      ...params,
      label: params.label,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getBoardColumnMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
