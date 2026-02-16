"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Users, Mic, Music, Image, Tag, Palette, FileText, type LucideIcon } from "lucide-react";
import axios from "axios";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../../components/ui/variants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import type { LibraryTab } from "./types";
import { API_BASE } from "../../constants";

type TabGuide = {
  icon: LucideIcon;
  title: string;
  description: string;
  tips: string[];
};

const GUIDES: Record<LibraryTab, TabGuide> = {
  characters: {
    icon: Users,
    title: "Characters",
    description: "일관된 이미지 생성을 위한 캐릭터 프로필을 관리합니다.",
    tips: [
      "LoRA 모델을 추가하면 외형 유사도가 높아집니다",
      "프리뷰 잠금으로 레퍼런스 이미지를 고정하세요",
      "커스텀 베이스 프롬프트로 스타일을 오버라이드할 수 있습니다",
    ],
  },
  voices: {
    icon: Mic,
    title: "Voices",
    description: "나레이션용 음성 프리셋을 생성하고 관리합니다.",
    tips: [
      "음성 성격을 상세히 설명할수록 품질이 좋아집니다",
      "저장 전 미리듣기로 품질을 확인하세요",
      "하나의 프리셋을 여러 스토리보드에서 재사용할 수 있습니다",
    ],
  },
  music: {
    icon: Music,
    title: "Music",
    description: "AI로 배경음악 프리셋을 생성합니다.",
    tips: [
      "장르 + 분위기 키워드를 프롬프트에 활용하세요",
      "클립당 최대 47초까지 생성 가능합니다",
      "씬에 추가하기 전 미리듣기로 확인하세요",
    ],
  },
  backgrounds: {
    icon: Image,
    title: "Backgrounds",
    description: "씬 생성에 사용할 레퍼런스 배경을 업로드합니다.",
    tips: [
      "태그를 추가하면 자동 매칭 정확도가 높아집니다",
      "카테고리로 장소별 정리가 가능합니다",
      "가중치가 높을수록 시각적 영향이 강해집니다",
    ],
  },
  tags: {
    icon: Tag,
    title: "Tags",
    description: "프롬프트 생성용 Danbooru 표준 태그를 관리합니다.",
    tips: [
      "태그는 언더스코어 형식을 사용합니다 (brown_hair)",
      "검토 대기 중인 태그를 확인하세요",
      "태그 규칙이 충돌을 자동으로 해결합니다",
    ],
  },
  style: {
    icon: Palette,
    title: "Styles",
    description: "SD 모델, 샘플러, 생성 설정을 구성합니다.",
    tips: [
      "SD WebUI가 --api 옵션으로 실행 중이어야 합니다",
      "새로고침으로 사용 가능한 모델을 동기화하세요",
      "스타일은 프로젝트 단위로 적용됩니다",
    ],
  },
  prompts: {
    icon: FileText,
    title: "Prompts",
    description: "프롬프트 템플릿을 조회하고 관리합니다.",
    tips: [
      "템플릿은 Jinja2 문법을 사용합니다",
      "12-Layer Builder가 최종 프롬프트를 구성합니다",
      "Prompt Validate 명령으로 테스트할 수 있습니다",
    ],
  },
};

type Character = {
  id: number;
  name: string;
  gender: string;
  base_prompt: string | null;
  lora_name: string | null;
  lora_weight: number | null;
  preview_locked: boolean;
  preview_url: string | null;
};

export default function LibrarySecondaryPanel({ activeTab }: { activeTab: LibraryTab }) {
  const searchParams = useSearchParams();
  const characterId = searchParams.get("id");
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === "characters" && characterId) {
      setLoading(true);
      axios
        .get(`${API_BASE}/characters/${characterId}`)
        .then((res) => setCharacter(res.data))
        .catch((err) => console.error("Failed to load character:", err))
        .finally(() => setLoading(false));
    } else {
      setCharacter(null);
    }
  }, [activeTab, characterId]);

  // Show character details if id parameter is present
  if (activeTab === "characters" && characterId) {
    if (loading) {
      return (
        <div className={SIDE_PANEL_CLASSES}>
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        </div>
      );
    }

    if (!character) {
      return (
        <div className={SIDE_PANEL_CLASSES}>
          <span className={SIDE_PANEL_LABEL}>
            <Users className="mr-1 inline h-3 w-3" />
            Character Not Found
          </span>
          <p className="text-xs text-zinc-500">Unable to load character details.</p>
        </div>
      );
    }

    return (
      <div className={SIDE_PANEL_CLASSES}>
        <span className={SIDE_PANEL_LABEL}>
          <Users className="mr-1 inline h-3 w-3" />
          Character Details
        </span>

        {character.preview_url && (
          <div className="mb-3 overflow-hidden rounded-lg border border-zinc-200">
            <img src={character.preview_url} alt={character.name} className="h-auto w-full" />
          </div>
        )}

        <div className="space-y-2">
          <div>
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Name
            </span>
            <p className="text-sm text-zinc-900">{character.name}</p>
          </div>

          <div>
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Gender
            </span>
            <p className="text-sm text-zinc-900">{character.gender}</p>
          </div>

          {character.lora_name && (
            <div>
              <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
                LoRA
              </span>
              <p className="text-sm text-zinc-900">
                {character.lora_name}
                {character.lora_weight && ` (${character.lora_weight})`}
              </p>
            </div>
          )}

          {character.base_prompt && (
            <div>
              <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
                Base Prompt
              </span>
              <p className="text-xs leading-relaxed text-zinc-600">{character.base_prompt}</p>
            </div>
          )}

          <div>
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Preview
            </span>
            <p className="text-sm text-zinc-900">
              {character.preview_locked ? "🔒 Locked" : "🔓 Unlocked"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Default: show guide
  const guide = GUIDES[activeTab];
  const Icon = guide.icon;

  return (
    <div className={SIDE_PANEL_CLASSES}>
      <span className={SIDE_PANEL_LABEL}>
        <Icon className="mr-1 inline h-3 w-3" />
        {guide.title} Guide
      </span>
      <p className="text-xs leading-relaxed text-zinc-500">{guide.description}</p>
      <div className="space-y-1.5 pt-1">
        <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
          Tips
        </span>
        <ul className="space-y-1">
          {guide.tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-300" />
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
