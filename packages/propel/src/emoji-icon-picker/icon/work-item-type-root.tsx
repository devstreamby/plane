/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { WORK_ITEM_TYPE_ICONS } from "../work-item-type-icons";

type Props = {
  onChange: (value: { name: string; color: string }) => void;
  query: string;
};

export function WorkItemTypeIconsList({ query, onChange }: Props) {
  const normalizedQuery = query.trim().toLowerCase();
  const filteredIcons = WORK_ITEM_TYPE_ICONS.filter((icon) => icon.name.toLowerCase().includes(normalizedQuery));

  return filteredIcons.map((icon) => (
    <button
      key={icon.name}
      type="button"
      title={icon.name}
      aria-label={icon.name}
      className="flex h-16 w-full flex-col items-center justify-center gap-1.5 rounded-md text-11 text-secondary transition-colors hover:bg-layer-1 hover:text-primary focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
      onClick={() => onChange({ name: icon.name, color: icon.color })}
    >
      <icon.element width={24} height={24} />
      <span>{icon.name}</span>
    </button>
  ));
}
