/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Icon } from "@phosphor-icons/react";
import { ArchiveIcon } from "@phosphor-icons/react/dist/csr/Archive";
import { BellIcon } from "@phosphor-icons/react/dist/csr/Bell";
import { BookOpenTextIcon } from "@phosphor-icons/react/dist/csr/BookOpenText";
import { BookmarkSimpleIcon } from "@phosphor-icons/react/dist/csr/BookmarkSimple";
import { BriefcaseIcon } from "@phosphor-icons/react/dist/csr/Briefcase";
import { BugIcon } from "@phosphor-icons/react/dist/csr/Bug";
import { CalendarBlankIcon } from "@phosphor-icons/react/dist/csr/CalendarBlank";
import { ChartBarIcon } from "@phosphor-icons/react/dist/csr/ChartBar";
import { ChatCircleIcon } from "@phosphor-icons/react/dist/csr/ChatCircle";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/csr/CheckCircle";
import { CheckSquareIcon } from "@phosphor-icons/react/dist/csr/CheckSquare";
import { CircleIcon } from "@phosphor-icons/react/dist/csr/Circle";
import { ClipboardTextIcon } from "@phosphor-icons/react/dist/csr/ClipboardText";
import { ClockIcon } from "@phosphor-icons/react/dist/csr/Clock";
import { CloudIcon } from "@phosphor-icons/react/dist/csr/Cloud";
import { CodeIcon } from "@phosphor-icons/react/dist/csr/Code";
import { CompassIcon } from "@phosphor-icons/react/dist/csr/Compass";
import { CubeIcon } from "@phosphor-icons/react/dist/csr/Cube";
import { DatabaseIcon } from "@phosphor-icons/react/dist/csr/Database";
import { EnvelopeSimpleIcon } from "@phosphor-icons/react/dist/csr/EnvelopeSimple";
import { FileTextIcon } from "@phosphor-icons/react/dist/csr/FileText";
import { FlagIcon } from "@phosphor-icons/react/dist/csr/Flag";
import { FlaskIcon } from "@phosphor-icons/react/dist/csr/Flask";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { GearIcon } from "@phosphor-icons/react/dist/csr/Gear";
import { GitBranchIcon } from "@phosphor-icons/react/dist/csr/GitBranch";
import { GitPullRequestIcon } from "@phosphor-icons/react/dist/csr/GitPullRequest";
import { GlobeIcon } from "@phosphor-icons/react/dist/csr/Globe";
import { HashIcon } from "@phosphor-icons/react/dist/csr/Hash";
import { HeartIcon } from "@phosphor-icons/react/dist/csr/Heart";
import { KeyIcon } from "@phosphor-icons/react/dist/csr/Key";
import { KanbanIcon } from "@phosphor-icons/react/dist/csr/Kanban";
import { LightningIcon } from "@phosphor-icons/react/dist/csr/Lightning";
import { LightbulbIcon } from "@phosphor-icons/react/dist/csr/Lightbulb";
import { LinkIcon } from "@phosphor-icons/react/dist/csr/Link";
import { ListChecksIcon } from "@phosphor-icons/react/dist/csr/ListChecks";
import { LockIcon } from "@phosphor-icons/react/dist/csr/Lock";
import { MapPinIcon } from "@phosphor-icons/react/dist/csr/MapPin";
import { MegaphoneIcon } from "@phosphor-icons/react/dist/csr/Megaphone";
import { NotePencilIcon } from "@phosphor-icons/react/dist/csr/NotePencil";
import { PackageIcon } from "@phosphor-icons/react/dist/csr/Package";
import { PaperclipIcon } from "@phosphor-icons/react/dist/csr/Paperclip";
import { RocketLaunchIcon } from "@phosphor-icons/react/dist/csr/RocketLaunch";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import { SparkleIcon } from "@phosphor-icons/react/dist/csr/Sparkle";
import { SquaresFourIcon } from "@phosphor-icons/react/dist/csr/SquaresFour";
import { StarIcon } from "@phosphor-icons/react/dist/csr/Star";
import { TagIcon } from "@phosphor-icons/react/dist/csr/Tag";
import { TargetIcon } from "@phosphor-icons/react/dist/csr/Target";
import { TerminalWindowIcon } from "@phosphor-icons/react/dist/csr/TerminalWindow";
import { TreeStructureIcon } from "@phosphor-icons/react/dist/csr/TreeStructure";
import { TrendUpIcon } from "@phosphor-icons/react/dist/csr/TrendUp";
import { UserCircleIcon } from "@phosphor-icons/react/dist/csr/UserCircle";
import { UsersThreeIcon } from "@phosphor-icons/react/dist/csr/UsersThree";
import { WarningIcon } from "@phosphor-icons/react/dist/csr/Warning";
import { WrenchIcon } from "@phosphor-icons/react/dist/csr/Wrench";

export type TPhosphorIcon = {
  name: string;
  element: Icon;
};

export const PHOSPHOR_ICONS_LIST: TPhosphorIcon[] = [
  { name: "Archive", element: ArchiveIcon },
  { name: "Bell", element: BellIcon },
  { name: "BookOpenText", element: BookOpenTextIcon },
  { name: "BookmarkSimple", element: BookmarkSimpleIcon },
  { name: "Briefcase", element: BriefcaseIcon },
  { name: "Bug", element: BugIcon },
  { name: "CalendarBlank", element: CalendarBlankIcon },
  { name: "ChartBar", element: ChartBarIcon },
  { name: "ChatCircle", element: ChatCircleIcon },
  { name: "CheckCircle", element: CheckCircleIcon },
  { name: "CheckSquare", element: CheckSquareIcon },
  { name: "Circle", element: CircleIcon },
  { name: "ClipboardText", element: ClipboardTextIcon },
  { name: "Clock", element: ClockIcon },
  { name: "Cloud", element: CloudIcon },
  { name: "Code", element: CodeIcon },
  { name: "Compass", element: CompassIcon },
  { name: "Cube", element: CubeIcon },
  { name: "Database", element: DatabaseIcon },
  { name: "EnvelopeSimple", element: EnvelopeSimpleIcon },
  { name: "FileText", element: FileTextIcon },
  { name: "Flag", element: FlagIcon },
  { name: "Flask", element: FlaskIcon },
  { name: "Folder", element: FolderIcon },
  { name: "Gear", element: GearIcon },
  { name: "GitBranch", element: GitBranchIcon },
  { name: "GitPullRequest", element: GitPullRequestIcon },
  { name: "Globe", element: GlobeIcon },
  { name: "Hash", element: HashIcon },
  { name: "Heart", element: HeartIcon },
  { name: "Kanban", element: KanbanIcon },
  { name: "Key", element: KeyIcon },
  { name: "Lightning", element: LightningIcon },
  { name: "Lightbulb", element: LightbulbIcon },
  { name: "Link", element: LinkIcon },
  { name: "ListChecks", element: ListChecksIcon },
  { name: "Lock", element: LockIcon },
  { name: "MapPin", element: MapPinIcon },
  { name: "Megaphone", element: MegaphoneIcon },
  { name: "NotePencil", element: NotePencilIcon },
  { name: "Package", element: PackageIcon },
  { name: "Paperclip", element: PaperclipIcon },
  { name: "RocketLaunch", element: RocketLaunchIcon },
  { name: "ShieldCheck", element: ShieldCheckIcon },
  { name: "Sparkle", element: SparkleIcon },
  { name: "SquaresFour", element: SquaresFourIcon },
  { name: "Star", element: StarIcon },
  { name: "Tag", element: TagIcon },
  { name: "Target", element: TargetIcon },
  { name: "TerminalWindow", element: TerminalWindowIcon },
  { name: "TreeStructure", element: TreeStructureIcon },
  { name: "TrendUp", element: TrendUpIcon },
  { name: "UserCircle", element: UserCircleIcon },
  { name: "UsersThree", element: UsersThreeIcon },
  { name: "Warning", element: WarningIcon },
  { name: "Wrench", element: WrenchIcon },
];
