/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Link2 } from "lucide-react";
import type { ClipboardEvent, FormEvent, KeyboardEvent } from "react";
import { useState } from "react";
// plane imports
import { cn, parseVideoUrl } from "@plane/utils";
// local imports
import { ECustomVideoAttributeNames, ECustomVideoProvider } from "../types";
import { isValidProviderVideoId, moveCursorAfterVideoNode } from "../utils";
import type { CustomVideoNodeViewProps } from "./node-view";

// Same story as Enter: the editor's own paste handler (for turning
// dropped/pasted files into image or video blocks) is bound on the
// ProseMirror view container and runs in the bubble phase, so it swallows a
// paste before it ever reaches this input's native paste behavior. Stopping
// it here in the capture phase lets the browser paste clipboard text into
// the field like a normal input.
const handlePasteCapture = (e: ClipboardEvent<HTMLInputElement>) => {
  e.stopPropagation();
};

export function CustomVideoEmbedInput(props: CustomVideoNodeViewProps) {
  const { editor, getPos, updateAttributes } = props;
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const isEditable = editor.isEditable;

  const submit = () => {
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
    moveCursorAfterVideoNode(editor, getPos);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  // The editor's own keymap (e.g. "Enter splits the block") binds Enter on
  // the ProseMirror view container, which sits between this input and the
  // document root — its listener runs during the bubble phase, before a
  // normal onKeyDown here would ever get a chance to stop it. Intercepting
  // in the capture phase (which runs root-to-target, ahead of that bubble
  // listener) is the only reliable way to make Enter submit this form
  // instead of falling through to the editor.
  const handleKeyDownCapture = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      submit();
    }
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
          onKeyDownCapture={handleKeyDownCapture}
          onPasteCapture={handlePasteCapture}
          placeholder="Paste a YouTube, Vimeo, Rutube, or VK link"
          className="flex-1 bg-transparent text-14 text-primary outline-none placeholder:text-tertiary"
          // eslint-disable-next-line jsx-a11y/no-autofocus -- this input only exists because the user just clicked "Embed link"; without autofocus, typing goes nowhere (matches the same pattern in components/links/link-edit-view.tsx)
          autoFocus
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
