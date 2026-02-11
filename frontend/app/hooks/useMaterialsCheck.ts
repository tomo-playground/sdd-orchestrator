import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";

export type MaterialStatus = {
  ready: boolean;
  count?: number;
  detail?: string;
};

export type MaterialsData = {
  storyboard_id: number;
  script: MaterialStatus;
  characters: MaterialStatus;
  voice: MaterialStatus;
  music: MaterialStatus;
  background: MaterialStatus;
};

export function useMaterialsCheck(storyboardId: number | null) {
  const [data, setData] = useState<MaterialsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!storyboardId) {
      setData(null);
      return;
    }
    setIsLoading(true);
    axios
      .get(`${API_BASE}/storyboards/${storyboardId}/materials`)
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setIsLoading(false));
  }, [storyboardId]);

  return { data, isLoading };
}
