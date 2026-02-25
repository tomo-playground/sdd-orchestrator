// ── Types ────────────────────────────────────────────────────

export type TemplateTag = {
  name: string;
  groupName: string;
  isPermanent: boolean;
};

export type WizardTemplate = {
  id: string;
  name: string;
  emoji: string;
  description: string;
  gender: "female" | "male";
  tags: TemplateTag[];
};

export type WizardCategory = {
  groupName: string;
  label: string;
  selectMode: "single" | "multi";
  maxSelect?: number;
  isPermanent: boolean;
  hasColorDot: boolean;
  defaultOpen: boolean;
  isRequired?: boolean;
};

// ── Categories ───────────────────────────────────────────────

export const WIZARD_CATEGORIES: WizardCategory[] = [
  {
    groupName: "hair_color",
    label: "Hair Color",
    selectMode: "single",
    isPermanent: true,
    hasColorDot: true,
    defaultOpen: true,
  },
  {
    groupName: "hair_style",
    label: "Hair Style",
    selectMode: "single",
    isPermanent: true,
    hasColorDot: false,
    defaultOpen: true,
  },
  {
    groupName: "hair_length",
    label: "Hair Length",
    selectMode: "single",
    isPermanent: true,
    hasColorDot: false,
    defaultOpen: true,
  },
  {
    groupName: "eye_color",
    label: "Eye Color",
    selectMode: "single",
    isPermanent: true,
    hasColorDot: true,
    defaultOpen: false,
  },
  {
    groupName: "body_type",
    label: "Body Type",
    selectMode: "single",
    isPermanent: true,
    hasColorDot: false,
    defaultOpen: true,
    isRequired: true,
  },
  {
    groupName: "body_feature",
    label: "Body Features",
    selectMode: "multi",
    isPermanent: true,
    hasColorDot: false,
    defaultOpen: false,
  },
  {
    groupName: "clothing",
    label: "Clothing",
    selectMode: "multi",
    maxSelect: 5,
    isPermanent: false,
    hasColorDot: false,
    defaultOpen: false,
  },
];

// ── Color Dot Mapping ────────────────────────────────────────

export const TAG_COLOR_DOTS: Record<string, string> = {
  // Hair colors
  black_hair: "bg-zinc-900",
  brown_hair: "bg-amber-700",
  blonde_hair: "bg-yellow-400",
  light_brown_hair: "bg-amber-500",
  red_hair: "bg-red-500",
  blue_hair: "bg-blue-500",
  pink_hair: "bg-pink-400",
  white_hair: "bg-white border border-zinc-300",
  silver_hair: "bg-zinc-300",
  green_hair: "bg-green-500",
  purple_hair: "bg-purple-500",
  orange_hair: "bg-orange-500",
  grey_hair: "bg-zinc-400",
  // Eye colors
  blue_eyes: "bg-blue-500",
  brown_eyes: "bg-amber-700",
  green_eyes: "bg-green-500",
  red_eyes: "bg-red-500",
  purple_eyes: "bg-purple-500",
  yellow_eyes: "bg-yellow-400",
  pink_eyes: "bg-pink-400",
  black_eyes: "bg-zinc-900",
  orange_eyes: "bg-orange-500",
  aqua_eyes: "bg-cyan-400",
  grey_eyes: "bg-zinc-400",
  golden_eyes: "bg-amber-500",
};

// ── Gender Identity Tags ─────────────────────────────────────

export const GENDER_IDENTITY_TAGS: Record<"female" | "male", string[]> = {
  female: ["1girl", "a_cute_girl"],
  male: ["1boy", "a_cute_boy"],
};

// ── Templates ────────────────────────────────────────────────

export const WIZARD_TEMPLATES: WizardTemplate[] = [
  {
    id: "anime_schoolgirl",
    name: "School Girl",
    emoji: "🎀",
    description: "Classic anime schoolgirl",
    gender: "female",
    tags: [
      { name: "brown_hair", groupName: "hair_color", isPermanent: true },
      { name: "long_hair", groupName: "hair_length", isPermanent: true },
      { name: "brown_eyes", groupName: "eye_color", isPermanent: true },
      { name: "slim", groupName: "body_type", isPermanent: true },
      { name: "school_uniform", groupName: "clothing", isPermanent: false },
    ],
  },
  {
    id: "anime_idol",
    name: "Idol",
    emoji: "🌟",
    description: "Cute idol character",
    gender: "female",
    tags: [
      { name: "pink_hair", groupName: "hair_color", isPermanent: true },
      { name: "twintails", groupName: "hair_style", isPermanent: true },
      { name: "medium_hair", groupName: "hair_length", isPermanent: true },
      { name: "blue_eyes", groupName: "eye_color", isPermanent: true },
      { name: "petite", groupName: "body_type", isPermanent: true },
    ],
  },
  {
    id: "cool_boy",
    name: "Cool Boy",
    emoji: "🔥",
    description: "Stylish anime boy",
    gender: "male",
    tags: [
      { name: "black_hair", groupName: "hair_color", isPermanent: true },
      { name: "short_hair", groupName: "hair_length", isPermanent: true },
      { name: "blue_eyes", groupName: "eye_color", isPermanent: true },
      { name: "slim", groupName: "body_type", isPermanent: true },
    ],
  },
  {
    id: "fantasy_girl",
    name: "Fantasy",
    emoji: "🧝",
    description: "Elf or fantasy character",
    gender: "female",
    tags: [
      { name: "silver_hair", groupName: "hair_color", isPermanent: true },
      { name: "long_hair", groupName: "hair_length", isPermanent: true },
      { name: "purple_eyes", groupName: "eye_color", isPermanent: true },
      { name: "pointy_ears", groupName: "body_feature", isPermanent: true },
      { name: "slim", groupName: "body_type", isPermanent: true },
    ],
  },
  {
    id: "blank",
    name: "Blank",
    emoji: "📝",
    description: "Start from scratch",
    gender: "female",
    tags: [],
  },
];
