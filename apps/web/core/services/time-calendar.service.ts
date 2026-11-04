/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IWorkingHours } from "@plane/types";
import { APIService } from "./api.service";

export type TTimeCalendarScheduleDay = {
  date: string;
  working: boolean;
  start: string | null;
  end: string | null;
};

export type TTimeCalendarLog = {
  id: string;
  project_id: string;
  issue_id: string;
  user_id: string | null;
  date: string;
  started_at: string;
  stopped_at: string | null;
  duration_seconds: number;
  stop_reason: "state_change" | "working_hours" | "manual_entry" | null;
  can_manage: boolean;
  issue: {
    name: string;
    sequence_id: number;
    project_identifier: string;
  };
};

export type TTimeCalendarResponse = {
  start_date: string;
  end_date: string;
  timezone: string;
  working_hours: IWorkingHours;
  schedule: TTimeCalendarScheduleDay[];
  can_view_others: boolean;
  editable_project_ids: string[];
  logs: TTimeCalendarLog[];
};

export type TTimeCalendarParams = {
  start_date: string;
  end_date: string;
  user_id?: string;
};

export class TimeCalendarService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getTimeLogs(workspaceSlug: string, params: TTimeCalendarParams): Promise<TTimeCalendarResponse> {
    return this.get(`/api/workspaces/${workspaceSlug}/time-logs/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const timeCalendarService = new TimeCalendarService();
