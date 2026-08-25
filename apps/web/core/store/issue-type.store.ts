/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set, unset } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type { TIssueType, TIssueTypePayload } from "@plane/types";
// services
import { IssueTypeService } from "@/services/issue/issue_type.service";
// store
import type { CoreRootStore } from "./root.store";

export interface IIssueTypeStore {
  // observable
  issueTypeMap: Record<string, Record<string, TIssueType>>;
  fetchedMap: Record<string, boolean>;
  // computed
  currentProjectIssueTypes: TIssueType[] | undefined;
  // computed actions
  getProjectIssueTypes: (projectId: string | null | undefined) => TIssueType[];
  getProjectIssueTypeIds: (projectId: string | null | undefined) => string[];
  getIssueTypeById: (
    projectId: string | null | undefined,
    issueTypeId: string | null | undefined
  ) => TIssueType | undefined;
  getProjectDefaultIssueType: (projectId: string | null | undefined) => TIssueType | undefined;
  // fetch actions
  fetchProjectIssueTypes: (workspaceSlug: string, projectId: string) => Promise<TIssueType[]>;
  // crud actions
  createIssueType: (workspaceSlug: string, projectId: string, data: TIssueTypePayload) => Promise<TIssueType>;
  updateIssueType: (
    workspaceSlug: string,
    projectId: string,
    issueTypeId: string,
    data: TIssueTypePayload
  ) => Promise<TIssueType>;
  deleteIssueType: (workspaceSlug: string, projectId: string, issueTypeId: string) => Promise<void>;
  markAsDefault: (workspaceSlug: string, projectId: string, issueTypeId: string) => Promise<TIssueType>;
}

export class IssueTypeStore implements IIssueTypeStore {
  // root store
  rootStore;
  // observable
  issueTypeMap: Record<string, Record<string, TIssueType>> = {};
  fetchedMap: Record<string, boolean> = {};
  // services
  issueTypeService;

  constructor(_rootStore: CoreRootStore) {
    makeObservable(this, {
      issueTypeMap: observable,
      fetchedMap: observable,
      currentProjectIssueTypes: computed,

      fetchProjectIssueTypes: action,
      createIssueType: action,
      updateIssueType: action,
      deleteIssueType: action,
      markAsDefault: action,
    });

    this.rootStore = _rootStore;
    this.issueTypeService = new IssueTypeService();
  }

  /**
   * Returns the work item types of the project currently open in the router
   */
  get currentProjectIssueTypes() {
    const projectId = this.rootStore.router.projectId;
    return this.getProjectIssueTypes(projectId);
  }

  getProjectIssueTypes = computedFn((projectId: string | null | undefined): TIssueType[] => {
    if (!projectId || !this.fetchedMap[projectId]) return [];
    // `Object.values` already returns a fresh array, so sorting in place mutates nothing shared.
    // eslint-disable-next-line unicorn/no-array-sort
    return Object.values(this.issueTypeMap[projectId] ?? {}).sort((a, b) => a.level - b.level);
  });

  getProjectIssueTypeIds = computedFn((projectId: string | null | undefined): string[] =>
    this.getProjectIssueTypes(projectId).map((type) => type.id)
  );

  getIssueTypeById = computedFn(
    (projectId: string | null | undefined, issueTypeId: string | null | undefined): TIssueType | undefined => {
      if (!projectId || !issueTypeId) return undefined;
      return this.issueTypeMap[projectId]?.[issueTypeId];
    }
  );

  getProjectDefaultIssueType = computedFn((projectId: string | null | undefined): TIssueType | undefined =>
    this.getProjectIssueTypes(projectId).find((type) => type.is_default)
  );

  /**
   * Fetches the work item types available to a project. Lazily seeded on the
   * backend the first time a project with the feature enabled is queried.
   */
  fetchProjectIssueTypes = async (workspaceSlug: string, projectId: string) => {
    const response = await this.issueTypeService.getProjectIssueTypes(workspaceSlug, projectId);
    runInAction(() => {
      set(this.issueTypeMap, [projectId], Object.fromEntries(response.map((type) => [type.id, type])));
      set(this.fetchedMap, projectId, true);
    });
    return response;
  };

  createIssueType = async (workspaceSlug: string, projectId: string, data: TIssueTypePayload) => {
    const response = await this.issueTypeService.createIssueType(workspaceSlug, projectId, data);
    runInAction(() => {
      set(this.issueTypeMap, [projectId, response.id], response);
    });
    return response;
  };

  updateIssueType = async (workspaceSlug: string, projectId: string, issueTypeId: string, data: TIssueTypePayload) => {
    const original = this.issueTypeMap[projectId]?.[issueTypeId];
    try {
      runInAction(() => {
        if (original) set(this.issueTypeMap, [projectId, issueTypeId], { ...original, ...data });
      });
      const response = await this.issueTypeService.updateIssueType(workspaceSlug, projectId, issueTypeId, data);
      runInAction(() => {
        set(this.issueTypeMap, [projectId, issueTypeId], response);
      });
      return response;
    } catch (error) {
      runInAction(() => {
        if (original) set(this.issueTypeMap, [projectId, issueTypeId], original);
      });
      throw error;
    }
  };

  deleteIssueType = async (workspaceSlug: string, projectId: string, issueTypeId: string) => {
    await this.issueTypeService.deleteIssueType(workspaceSlug, projectId, issueTypeId);
    runInAction(() => {
      // Drop the entry outright. Marking it `is_active: false` used to leave the row
      // on screen, because neither this store nor the list endpoint filters on
      // `is_active` — that flag is the activate/deactivate toggle, not a delete marker.
      unset(this.issueTypeMap, [projectId, issueTypeId]);
    });
  };

  markAsDefault = async (workspaceSlug: string, projectId: string, issueTypeId: string) => {
    const response = await this.issueTypeService.markAsDefault(workspaceSlug, projectId, issueTypeId);
    runInAction(() => {
      Object.values(this.issueTypeMap[projectId] ?? {}).forEach((type) => {
        if (type.id === issueTypeId) return;
        if (type.is_default) set(this.issueTypeMap, [projectId, type.id], { ...type, is_default: false });
      });
      set(this.issueTypeMap, [projectId, response.id], response);
    });
    return response;
  };
}
