/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// extensions
import type { ImageExtensionStorage } from "@/extensions/image";
import type { CustomVideoExtensionStorage } from "@/extensions/custom-video/types";

export type ExtensionFileSetStorageKey =
  | Extract<keyof ImageExtensionStorage, "deletedImageSet">
  | Extract<keyof CustomVideoExtensionStorage, "deletedVideoSet">;
