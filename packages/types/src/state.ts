/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TStateGroups = "backlog" | "unstarted" | "started" | "completed" | "cancelled";

export interface IState {
  readonly id: string;
  color: string;
  default: boolean;
  description: string;
  group: TStateGroups;
  name: string;
  project_id: string;
  sequence: number;
  workspace_id: string;
  order: number;
  allow_any_transition?: boolean;
}

/** Workflow: allowed transitions keyed by source state id. A state absent from the map allows every target. */
export type TStateTransitionMap = Record<string, string[]>;

export type TStateTransitionPayload = {
  transitions: TStateTransitionMap;
};

/** Board: a column of the project board, owning one or more states. */
export interface TBoardColumn {
  readonly id: string;
  name: string;
  sequence: number;
  project_id: string;
  workspace_id: string;
  state_ids: string[];
}

export type TBoardColumnPayload = {
  name?: string;
  sequence?: number;
  state_ids?: string[];
};

export interface IStateLite {
  color: string;
  group: TStateGroups;
  id: string;
  name: string;
}

export interface IStateResponse {
  [key: string]: IState[];
}

export type TStateOperationsCallbacks = {
  createState: (data: Partial<IState>) => Promise<IState>;
  updateState: (stateId: string, data: Partial<IState>) => Promise<IState | undefined>;
  deleteState: (stateId: string) => Promise<void>;
  moveStatePosition: (stateId: string, data: Partial<IState>) => Promise<void>;
  markStateAsDefault: (stateId: string) => Promise<void>;
};
