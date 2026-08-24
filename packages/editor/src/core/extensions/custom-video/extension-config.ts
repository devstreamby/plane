/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes, Node } from "@tiptap/core";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";
// local imports
import { ECustomVideoAttributeNames } from "./types";
import type {
  CustomVideoExtensionOptions,
  TCustomVideoAttributes,
  CustomVideoExtensionType,
  CustomVideoExtensionStorage,
  InsertVideoComponentProps,
  InsertVideoEmbedProps,
} from "./types";
import { DEFAULT_CUSTOM_VIDEO_ATTRIBUTES } from "./utils";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    [CORE_EXTENSIONS.CUSTOM_VIDEO]: {
      insertVideoComponent: ({ file, pos, event }: InsertVideoComponentProps) => ReturnType;
      insertVideoEmbed: ({ provider, videoId, pos }: InsertVideoEmbedProps) => ReturnType;
    };
  }
  interface Storage {
    [CORE_EXTENSIONS.CUSTOM_VIDEO]: CustomVideoExtensionStorage;
  }
}

export const CustomVideoExtensionConfig: CustomVideoExtensionType = Node.create<
  CustomVideoExtensionOptions,
  CustomVideoExtensionStorage
>({
  name: CORE_EXTENSIONS.CUSTOM_VIDEO,
  group: "block",
  atom: true,

  addAttributes() {
    return Object.values(ECustomVideoAttributeNames).reduce(
      (acc, value) => {
        acc[value] = {
          default: DEFAULT_CUSTOM_VIDEO_ATTRIBUTES[value],
        };
        return acc;
      },
      {} as Record<ECustomVideoAttributeNames, { default: TCustomVideoAttributes[ECustomVideoAttributeNames] }>
    );
  },

  parseHTML() {
    return [
      {
        tag: "video-component",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ["video-component", mergeAttributes(HTMLAttributes)];
  },
});
