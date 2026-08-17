/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType, SVGProps } from "react";

export type TWorkItemTypeIcon = ComponentType<SVGProps<SVGSVGElement>>;

const sharedProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  xmlns: "http://www.w3.org/2000/svg",
  "aria-hidden": true,
} as const;

export function TaskWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <rect x="3" y="3" width="18" height="18" rx="5" fill="#2563EB" />
      <path
        d="m7.5 12.2 2.9 2.9 6.4-6.5"
        stroke="#FFF"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="18.25" cy="5.75" r="2.25" fill="#67E8F9" />
    </svg>
  );
}

export function StoryWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <path
        d="M3.5 5.8c0-1 .8-1.8 1.8-1.8h4.2c1.2 0 2.2.6 2.5 1.4V20c-.4-.9-1.4-1.5-2.6-1.5H5.3c-1 0-1.8-.8-1.8-1.8V5.8Z"
        fill="#059669"
      />
      <path
        d="M20.5 5.8c0-1-.8-1.8-1.8-1.8h-4.2c-1.2 0-2.2.6-2.5 1.4V20c.4-.9 1.4-1.5 2.6-1.5h4.1c1 0 1.8-.8 1.8-1.8V5.8Z"
        fill="#0D9488"
      />
      <path d="M6.5 8h3M6.5 11h3M14.5 8h3M14.5 11h3" stroke="#FFF" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="12" cy="4.5" r="2" fill="#FBBF24" />
    </svg>
  );
}

export function SubtaskWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="2.2" fill="#4F46E5" />
      <rect x="14" y="14" width="7" height="7" rx="2.2" fill="#06B6D4" />
      <path d="M6.5 10v3.2c0 2.4 1.9 4.3 4.3 4.3H14" stroke="#60A5FA" strokeWidth="2.2" strokeLinecap="round" />
      <path
        d="m11.5 14.8 2.7 2.7-2.7 2.7"
        stroke="#60A5FA"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="17.5" cy="6.5" r="2.5" fill="#A78BFA" />
    </svg>
  );
}

export function EpicWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <path d="M12 2.5 21.5 12 12 21.5 2.5 12 12 2.5Z" fill="#7C3AED" />
      <path d="m12 6 1.55 3.25L17 10.8l-3.45 1.55L12 16l-1.55-3.65L7 10.8l3.45-1.55L12 6Z" fill="#FFF" />
      <path d="m18.4 3.2.55 1.4 1.45.55-1.45.55-.55 1.45-.55-1.45-1.45-.55 1.45-.55.55-1.4Z" fill="#F472B6" />
    </svg>
  );
}

export function BugWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <path d="M8.2 7.5A3.8 3.8 0 0 1 12 3.7a3.8 3.8 0 0 1 3.8 3.8v1H8.2v-1Z" fill="#F97316" />
      <rect x="5.5" y="7" width="13" height="14" rx="6.5" fill="#E11D48" />
      <path
        d="M12 8v12M5.5 11H2.8M18.5 11h2.7M5.5 16H2.8M18.5 16h2.7M8.3 4.7 6.7 2.8M15.7 4.7l1.6-1.9"
        stroke="#FB7185"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="9.4" cy="11.2" r="1" fill="#FFF" />
      <circle cx="14.6" cy="11.2" r="1" fill="#FFF" />
    </svg>
  );
}

export function SpikeWorkItemIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      <path
        d="M8 3h8M10 3v5.2l-5.4 8.7A2.7 2.7 0 0 0 6.9 21h10.2a2.7 2.7 0 0 0 2.3-4.1L14 8.2V3"
        stroke="#F59E0B"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M7.3 16.2h9.4l1.2 2a1.2 1.2 0 0 1-1 1.8H7.1a1.2 1.2 0 0 1-1-1.8l1.2-2Z" fill="#8B5CF6" />
      <circle cx="13.8" cy="13" r="1.4" fill="#F472B6" />
      <circle cx="10.4" cy="11.2" r="1" fill="#FBBF24" />
      <path d="m18.4 4.2.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6.6-1.4Z" fill="#22D3EE" />
    </svg>
  );
}

export const WORK_ITEM_TYPE_ICONS = [
  { name: "Story", element: StoryWorkItemIcon, color: "#059669" },
  { name: "Task", element: TaskWorkItemIcon, color: "#2563EB" },
  { name: "Subtask", element: SubtaskWorkItemIcon, color: "#4F46E5" },
  { name: "Epic", element: EpicWorkItemIcon, color: "#7C3AED" },
  { name: "Bug", element: BugWorkItemIcon, color: "#E11D48" },
  { name: "Spike", element: SpikeWorkItemIcon, color: "#F59E0B" },
] satisfies { name: string; element: TWorkItemTypeIcon; color: string }[];
