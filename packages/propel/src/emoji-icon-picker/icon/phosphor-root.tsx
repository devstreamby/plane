/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PHOSPHOR_ICONS_LIST } from "../phosphor-icons";

type Props = {
  onChange: (value: { name: string; color: string }) => void;
  activeColor: string;
  query: string;
};

export function PhosphorIconsList(props: Props) {
  const { query, onChange, activeColor } = props;
  const normalizedQuery = query.trim().toLowerCase();
  const filteredIcons = PHOSPHOR_ICONS_LIST.filter((icon) => icon.name.toLowerCase().includes(normalizedQuery));

  return filteredIcons.map((icon) => (
    <button
      key={icon.name}
      type="button"
      title={icon.name}
      aria-label={icon.name}
      className="grid h-9 w-9 place-items-center rounded-sm select-none hover:bg-layer-1"
      onClick={() => onChange({ name: icon.name, color: activeColor })}
    >
      <icon.element color={activeColor} size={18} weight="duotone" />
    </button>
  ));
}
