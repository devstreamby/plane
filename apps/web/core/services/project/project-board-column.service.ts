/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TBoardColumn, TBoardColumnPayload } from "@plane/types";
import { APIService } from "@/services/api.service";

export class ProjectBoardColumnService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getBoardColumns(workspaceSlug: string, projectId: string): Promise<TBoardColumn[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/board-columns/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createBoardColumn(workspaceSlug: string, projectId: string, data: TBoardColumnPayload): Promise<TBoardColumn> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/board-columns/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateBoardColumn(
    workspaceSlug: string,
    projectId: string,
    columnId: string,
    data: TBoardColumnPayload
  ): Promise<TBoardColumn> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/board-columns/${columnId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteBoardColumn(workspaceSlug: string, projectId: string, columnId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/projects/${projectId}/board-columns/${columnId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
