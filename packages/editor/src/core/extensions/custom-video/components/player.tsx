/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AlertTriangle, ExternalLink, Film, PlayCircle, Youtube } from "lucide-react";
import { useEffect, useState } from "react";
// local imports
import { ECustomVideoProvider, ECustomVideoSource } from "../types";
import { buildProviderVideoUrl, fetchVideoOEmbed, isValidProviderVideoId } from "../utils";
import type { TVideoOEmbedResult } from "../utils";
import type { CustomVideoNodeViewProps } from "./node-view";

const PROVIDER_LABELS: Record<ECustomVideoProvider, string> = {
  [ECustomVideoProvider.YOUTUBE]: "YouTube",
  [ECustomVideoProvider.VIMEO]: "Vimeo",
  [ECustomVideoProvider.RUTUBE]: "Rutube",
  [ECustomVideoProvider.VK]: "VK",
  [ECustomVideoProvider.DIRECT]: "video",
};

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

type TOEmbedState = { status: "loading" } | { status: "loaded"; data: TVideoOEmbedResult } | { status: "error" };

function VideoLinkPreviewCard({ provider, videoId }: { provider: ECustomVideoProvider; videoId: string }) {
  const [state, setState] = useState<TOEmbedState>({ status: "loading" });
  const pageUrl = buildProviderVideoUrl(provider, videoId);
  const providerLabel = PROVIDER_LABELS[provider];

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    fetchVideoOEmbed(provider, videoId)
      .then((data) => {
        if (cancelled) return;
        return setState(data ? { status: "loaded", data } : { status: "error" });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });

    return () => {
      cancelled = true;
    };
  }, [provider, videoId]);

  return (
    <a
      href={pageUrl}
      target="_blank"
      rel="noopener noreferrer"
      contentEditable={false}
      className="video-link-preview-card group/video-card flex h-28 items-stretch overflow-hidden rounded-lg border border-subtle bg-layer-3 no-underline transition-colors hover:border-strong"
    >
      <div className="relative h-full w-48 flex-shrink-0 bg-layer-2">
        {state.status === "loaded" && state.data.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- external, unregistered thumbnail host; next/image can't optimize it
          <img src={state.data.thumbnailUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center">
            {provider === ECustomVideoProvider.YOUTUBE ? (
              <Youtube className="size-8 text-tertiary" />
            ) : (
              <Film className="size-8 text-tertiary" />
            )}
          </div>
        )}
        {state.status !== "error" && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/10 opacity-0 transition-opacity group-hover/video-card:opacity-100">
            <PlayCircle className="size-9 text-white drop-shadow" />
          </div>
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1 px-3 py-2">
        <div className="line-clamp-2 text-14 font-medium text-primary">
          {state.status === "loaded" ? state.data.title : state.status === "loading" ? "Loading video…" : pageUrl}
        </div>
        {state.status === "loaded" && state.data.authorName && (
          <div className="truncate text-12 text-tertiary">{state.data.authorName}</div>
        )}
        <div className="mt-0.5 inline-flex w-fit items-center gap-1 text-12 font-medium text-secondary">
          <ExternalLink className="size-3" />
          Watch on {providerLabel}
        </div>
      </div>
    </a>
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

    return <VideoLinkPreviewCard provider={provider} videoId={videoId} />;
  }

  return null;
}
