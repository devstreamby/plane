/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export const ACCEPTED_AVATAR_IMAGE_MIME_TYPES_FOR_REACT_DROPZONE = {
  "image/jpeg": [],
  "image/jpg": [],
  "image/png": [],
  "image/webp": [],
};
export const ACCEPTED_COVER_IMAGE_MIME_TYPES_FOR_REACT_DROPZONE = {
  "image/jpeg": [],
  "image/jpg": [],
  "image/png": [],
  "image/webp": [],
};

/**
 * Dangerous file extensions that should be blocked
 */
export const DANGEROUS_EXTENSIONS = [
  "exe",
  "bat",
  "cmd",
  "sh",
  "php",
  "asp",
  "aspx",
  "jsp",
  "cgi",
  "dll",
  "vbs",
  "jar",
  "ps1",
];

/**
 * Extension -> MIME type fallback for files without a detectable binary signature
 * (plain text formats have no magic bytes for signature-based sniffing to find).
 * Only used when signature detection finds nothing, so it can never override a
 * type actually detected from the file's bytes (e.g. a renamed executable still
 * sniffs as its real binary type and never reaches this fallback).
 * Keep in sync with `ATTACHMENT_MIME_TYPES` in apps/api/plane/settings/common.py.
 */
export const EXTENSION_MIME_TYPE_MAP: Record<string, string> = {
  csv: "text/csv",
  txt: "text/plain",
  log: "text/plain",
  css: "text/css",
  json: "application/json",
  har: "application/json",
  md: "text/markdown",
  markdown: "text/markdown",
  xml: "text/xml",
  html: "text/html",
  htm: "text/html",
};
