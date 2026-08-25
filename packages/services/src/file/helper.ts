/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// external imports
import { fileTypeFromBuffer } from "file-type";
// plane imports
import type { TFileMetaDataLite, TFileSignedURLResponse } from "@plane/types";
import { DANGEROUS_EXTENSIONS, EXTENSION_MIME_TYPE_MAP } from "@plane/constants";

// A last-resort fallback (the browser's own File.type) is rejected if it comes back
// as this value -- it's already reachable via a legitimate server-allowed MIME
// (e.g. .obj files), so trusting it here would turn the fallback into a wildcard
// that accepts anything the OS couldn't identify either.
const GENERIC_BINARY_MIME_TYPE = "application/octet-stream";

/**
 * @description Filename validation - checks for double extensions and dangerous patterns
 * @param {string} filename
 * @returns {string | null} Error message if invalid, null if valid
 */
const validateFilename = (filename: string): string | null => {
  if (!filename || filename.trim().length === 0) {
    return "Filename cannot be empty";
  }

  // Check for dot files (e.g., .htaccess, .env)
  if (filename.startsWith(".")) {
    return "Hidden files (starting with dot) are not allowed";
  }

  // Check for path separators
  if (filename.includes("/") || filename.includes("\\")) {
    return "Filename cannot contain path separators";
  }

  const parts = filename.split(".");

  // Check for double extensions with dangerous patterns
  if (parts.length >= 3) {
    const secondLastExt = parts[parts.length - 2]?.toLowerCase() || "";
    if (DANGEROUS_EXTENSIONS.includes(secondLastExt)) {
      return "File has suspicious double extension";
    }
  }

  // Check if the actual extension is dangerous
  const extension = parts[parts.length - 1]?.toLowerCase() || "";
  if (DANGEROUS_EXTENSIONS.includes(extension)) {
    return `File extension '${extension}' is not allowed`;
  }

  return null;
};

/**
 * @description Look up a MIME type from a filename's extension using a hardcoded
 * map, for formats that have no binary signature to sniff (plain text formats:
 * csv, txt, css, json, html, ...).
 * @param {string} filename
 * @returns {string} the mapped MIME type, or an empty string if the extension isn't mapped
 */
const getMimeTypeFromExtension = (filename: string): string => {
  const parts = filename.split(".");
  if (parts.length < 2) return "";
  const extension = parts[parts.length - 1]?.toLowerCase() ?? "";
  return EXTENSION_MIME_TYPE_MAP[extension] ?? "";
};

/**
 * @description from the provided signed URL response, generate a payload to be used to upload the file
 * @param {TFileSignedURLResponse} signedURLResponse
 * @param {File} file
 * @returns {FormData} file upload request payload
 */
export const generateFileUploadPayload = (signedURLResponse: TFileSignedURLResponse, file: File): FormData => {
  const formData = new FormData();
  Object.entries(signedURLResponse.upload_data.fields).forEach(([key, value]) => formData.append(key, value));
  formData.append("file", file);
  return formData;
};

/**
 * @description Detect MIME type from file signature using file-type library
 * @param {File} file
 * @returns {Promise<string>} detected MIME type or empty string if unknown
 */
const detectMimeTypeFromSignature = async (file: File): Promise<string> => {
  try {
    // Read first 4KB which is usually sufficient for most file type detection
    const chunk = file.slice(0, 4096);
    const buffer = await chunk.arrayBuffer();
    const uint8Array = new Uint8Array(buffer);

    const fileType = await fileTypeFromBuffer(uint8Array);
    return fileType?.mime || "";
  } catch (_error) {
    return "";
  }
};

/**
 * @description Validate and detect the MIME type of a file. Tries, in order: binary
 * signature sniffing (authoritative -- catches renamed executables etc.), a
 * hardcoded extension map (for text formats with no signature to sniff), and
 * finally the browser's own `File.type` (best-effort, OS-dependent, so it's only
 * a last resort and never overrides an earlier match).
 * Also performs basic security checks on filename.
 * @param {File} file
 * @returns {Promise<string>} validated and detected MIME type
 */
const validateAndDetectFileType = async (file: File): Promise<string> => {
  // Basic filename validation
  const filenameError = validateFilename(file.name);
  if (filenameError) {
    console.warn(`File validation warning: ${filenameError}`);
  }

  try {
    const signatureType = await detectMimeTypeFromSignature(file);
    if (signatureType) {
      return signatureType;
    }
  } catch (_error) {
    console.warn("Error detecting file type from signature:", _error);
  }

  const extensionType = getMimeTypeFromExtension(file.name);
  if (extensionType) {
    return extensionType;
  }

  if (file.type && file.type !== GENERIC_BINARY_MIME_TYPE) {
    return file.type;
  }

  // fallback for unknown files
  return "";
};

/**
 * @description returns the necessary file meta data to upload a file
 * @param {File} file
 * @returns {Promise<TFileMetaDataLite>} payload with file info
 */
export const getFileMetaDataForUpload = async (file: File): Promise<TFileMetaDataLite> => {
  const fileType = await validateAndDetectFileType(file);
  return {
    name: file.name,
    size: file.size,
    type: fileType,
  };
};

/**
 * @description this function returns the assetId from the asset source
 * @param {string} src
 * @returns {string} assetId
 */
export const getAssetIdFromUrl = (src: string): string => {
  const sourcePaths = src.split("/");
  const assetUrl = sourcePaths[sourcePaths.length - 1];
  return assetUrl ?? "";
};
