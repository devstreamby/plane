/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Link2 } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
// plane imports
import { cn, parseVideoUrl } from "@plane/utils";
// local imports
import { ECustomVideoAttributeNames, ECustomVideoProvider } from "../types";
import { isValidProviderVideoId } from "../utils";
import type { CustomVideoNodeViewProps } from "./node-view";

export function CustomVideoEmbedInput(props: CustomVideoNodeViewProps) {
  const { editor, updateAttributes } = props;
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const isEditable = editor.isEditable;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    const parsed = parseVideoUrl(url);
    if (!parsed) {
      setError("Couldn't recognize this link. Paste a YouTube, Vimeo, Rutube, VK, or direct video URL.");
      return;
    }
    const provider = parsed.provider as ECustomVideoProvider;
    if (!isValidProviderVideoId(provider, parsed.videoId)) {
      setError("This link doesn't look right.");
      return;
    }

    updateAttributes({
      [ECustomVideoAttributeNames.PROVIDER]: provider,
      [ECustomVideoAttributeNames.VIDEO_ID]: parsed.videoId,
    });
  };

  if (!isEditable) {
    return (
      <div className="video-upload-component flex items-center gap-2 rounded-lg border border-dashed border-subtle bg-layer-3 px-2 py-3 text-tertiary">
        <Link2 className="size-4" />
        <div className="text-14">No video linked</div>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "video-upload-component rounded-lg border border-dashed bg-layer-3 px-2 py-2",
        error ? "border-danger-primary" : "border-subtle"
      )}
      contentEditable={false}
    >
      <div className="flex items-center gap-2">
        <Link2 className="size-4 flex-shrink-0 text-tertiary" />
        <input
          type="text"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError(undefined);
          }}
          placeholder="Paste a YouTube, Vimeo, Rutube, or VK link"
          className="flex-1 bg-transparent text-14 text-primary outline-none placeholder:text-tertiary"
        />
        <button
          type="submit"
          className="flex-shrink-0 rounded-md border border-subtle px-2 py-1 text-12 font-medium hover:bg-layer-3-hover"
        >
          Embed
        </button>
      </div>
      {error && <div className="mt-1.5 pl-6 text-12 text-danger-primary">{error}</div>}
    </form>
  );
}
