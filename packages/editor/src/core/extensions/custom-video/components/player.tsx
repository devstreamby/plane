/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
// local imports
import { ECustomVideoProvider, ECustomVideoSource } from "../types";
import { getVideoEmbedSrc, isValidProviderVideoId } from "../utils";
import type { CustomVideoNodeViewProps } from "./node-view";

function VideoErrorState({ message }: { message: string }) {
  return (
    <div
      className="video-upload-component border-danger-primary flex items-center gap-2 rounded-lg border border-dashed bg-danger-subtle px-2 py-3 text-danger-primary"
      contentEditable={false}
    >
      <AlertTriangle className="size-4 flex-shrink-0" />
      <div className="text-14">{message}</div>
    </div>
  );
}

export function CustomVideoPlayer(props: CustomVideoNodeViewProps) {
  const { extension, node } = props;
  const { source, src: assetId, provider, videoid: videoId } = node.attrs;

  const [resolvedSrc, setResolvedSrc] = useState<string | undefined>(undefined);
  const [failedToLoad, setFailedToLoad] = useState(false);

  useEffect(() => {
    if (source !== ECustomVideoSource.UPLOAD || !assetId) return;
    let cancelled = false;
    setResolvedSrc(undefined);
    setFailedToLoad(false);

    const resolveSource = async () => {
      try {
        const url = await extension.options.getVideoSource?.(assetId);
        if (!cancelled) setResolvedSrc(url);
      } catch (error) {
        console.error("Error fetching video source:", error);
        if (!cancelled) setFailedToLoad(true);
      }
    };
    void resolveSource();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, assetId, extension.options.getVideoSource]);

  if (source === ECustomVideoSource.UPLOAD) {
    if (failedToLoad) return <VideoErrorState message="Couldn't load this video." />;
    if (!resolvedSrc) {
      return (
        <div
          className="video-upload-component flex h-40 items-center justify-center rounded-lg border border-subtle bg-layer-3 text-tertiary"
          contentEditable={false}
        >
          Loading video…
        </div>
      );
    }
    return (
      <div className="relative" contentEditable={false}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video src={resolvedSrc} controls preload="metadata" className="max-h-[480px] w-full rounded-lg bg-black" />
      </div>
    );
  }

  if (source === ECustomVideoSource.EXTERNAL && provider && videoId) {
    if (!isValidProviderVideoId(provider, videoId)) {
      return <VideoErrorState message="This video link is no longer valid." />;
    }

    if (provider === ECustomVideoProvider.DIRECT) {
      return (
        <div className="relative" contentEditable={false}>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video src={videoId} controls preload="metadata" className="max-h-[480px] w-full rounded-lg bg-black" />
        </div>
      );
    }

    const embedSrc = getVideoEmbedSrc(provider, videoId);
    if (!embedSrc) return <VideoErrorState message="Unsupported video provider." />;

    return (
      <div
        className="relative w-full overflow-hidden rounded-lg bg-black"
        style={{ aspectRatio: "16 / 9" }}
        contentEditable={false}
      >
        <iframe
          src={embedSrc}
          className="absolute inset-0 h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
          sandbox="allow-scripts allow-presentation allow-popups"
          title="Embedded video"
        />
      </div>
    );
  }

  return null;
}
